// Face-only inference and a 32-byte paged I2C interface for Arduino Uno.
#include <cstdio>
#include <cmath>
#include <cstring>
#include <algorithm>
#include "WE2_device.h"
#include "WE2_core.h"
#include "board.h"
#include "cvapp_yolov8n_ob.h"
#include "cisdp_sensor.h"
#include "memory_manage.h"
#include "img_proc_helium.h"
#include "hx_drv_iic.h"
#include "hx_drv_scu.h"
#include "xprintf.h"
#include "ethosu_driver.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/schema/schema_generated.h"
#include "face_expected_model.h"

namespace {
constexpr int kSize = 192;
// Verified camera mounting: turn the input 90 degrees clockwise for detection.
constexpr bool kRotateClockwise = true;
constexpr int kMaxFaces = 16;
constexpr int kArenaBytes = 1053*1024;
constexpr int kMaxCandidates = 128;
struct Face { float x, y, w, h, score; };
struct Result { Face faces[kMaxFaces]; uint16_t frame, width, height; uint8_t count, state; };
static Result published = {};
static uint8_t packet[32];
static uint8_t page = 0;
static uint16_t frame = 0;
static ethosu_driver npu;
static tflite::MicroInterpreter* interpreter = nullptr;
static TfLiteTensor* input = nullptr;
static Face candidates[kMaxCandidates];

void npu_irq() { ethosu_irq_handler(&npu); }
void put16(int offset, uint16_t value) { packet[offset]=value&255; packet[offset+1]=value>>8; }
uint16_t clamp16(float value) { return static_cast<uint16_t>(std::max(0.f, std::min(65535.f, value))); }
void make_packet() {
    std::memset(packet, 0, sizeof(packet));
    packet[0]='F'; packet[1]='D'; packet[2]=1; packet[3]=published.state;
    put16(4,published.frame); packet[6]=published.count; packet[7]=page;
    put16(8,published.width); put16(10,published.height);
    for (int i=0; i<2; ++i) {
        int index=page*2+i;
        if(index>=published.count) break;
        const Face& face=published.faces[index];
        int offset=12+10*i;
        put16(offset,clamp16(face.x)); put16(offset+2,clamp16(face.y));
        put16(offset+4,clamp16(face.w)); put16(offset+6,clamp16(face.h));
        packet[offset+8]=static_cast<uint8_t>(face.score*100.f+0.5f);
    }
}
void tx_done(void*) {
    int pages=std::max(1,(published.count+1)/2);
    page=(page+1)%pages;
    make_packet();
    hx_drv_i2cs_interrupt_write(USE_DW_IIC_SLV_0,0x62,packet,sizeof(packet),(void*)tx_done);
}
void i2c_error(void* param) {
    auto* dev=static_cast<HX_DRV_DEV_IIC*>(param);
    if(dev->iic_info.err_state==DEV_IIC_ERR_TX_DATA_UNREADY) {
        page=0; make_packet();
        hx_drv_i2cs_interrupt_write(USE_DW_IIC_SLV_0,0x62,packet,sizeof(packet),(void*)tx_done);
    }
}
void init_i2c() {
    hx_drv_scu_set_PA2_pinmux(SCU_PA2_PINMUX_SB_I2C_S_SCL_0,1);
    hx_drv_scu_set_PA3_pinmux(SCU_PA3_PINMUX_SB_I2C_S_SDA_0,1);
    hx_drv_i2cs_init(USE_DW_IIC_SLV_0,HX_I2C_HOST_SLV_0_BASE);
    hx_drv_i2cs_set_err_cb(USE_DW_IIC_SLV_0,(void*)i2c_error);
    make_packet();
    hx_drv_i2cs_interrupt_write(USE_DW_IIC_SLV_0,0x62,packet,sizeof(packet),(void*)tx_done);
}
float tensor_value(const TfLiteTensor* t,int y,int x,int c,int height,int width,bool nhwc) {
    int index=nhwc ? (y*width+x)*65+c : c*height*width+y*width+x;
    return (t->data.int8[index]-t->params.zero_point)*t->params.scale;
}
float sigmoid(float value) { return 1.f/(1.f+std::exp(-value)); }
float distance(const TfLiteTensor* t,int y,int x,int side,int h,int w,bool nhwc) {
    float logits[16], maximum=-1e30f, weighted=0, total=0;
    for(int j=0;j<16;++j) {
        logits[j]=tensor_value(t,y,x,side*16+j,h,w,nhwc);
        maximum=std::max(maximum,logits[j]);
    }
    for(int j=0;j<16;++j) {
        float p=std::exp(logits[j]-maximum); total+=p; weighted+=p*j;
    }
    return weighted/total;
}
float iou(const Face& a,const Face& b) {
    float w=std::max(0.f,std::min(a.x+a.w,b.x+b.w)-std::max(a.x,b.x));
    float h=std::max(0.f,std::min(a.y+a.h,b.y+b.h)-std::max(a.y,b.y));
    float intersection=w*h;
    float total=a.w*a.h+b.w*b.h-intersection;
    return total>0 ? intersection/total : 0;
}
bool decode(Result& result) {
    int count=0;
    for(int branch=0;branch<3;++branch) {
        TfLiteTensor* out=interpreter->output(branch);
        if(out->type!=kTfLiteInt8 || out->dims->size!=4) return false;
        bool nhwc=out->dims->data[3]==65;
        int h=out->dims->data[nhwc?1:2],w=out->dims->data[nhwc?2:3];
        if((!nhwc && out->dims->data[1]!=65) || h!=w || (h!=24 && h!=12 && h!=6)) return false;
        float stride=static_cast<float>(kSize)/h;
        for(int y=0;y<h;++y) for(int x=0;x<w;++x) {
            float score=sigmoid(tensor_value(out,y,x,64,h,w,nhwc));
            if(score<0.35f) continue;
            float left=distance(out,y,x,0,h,w,nhwc)*stride;
            float top=distance(out,y,x,1,h,w,nhwc)*stride;
            float right=distance(out,y,x,2,h,w,nhwc)*stride;
            float bottom=distance(out,y,x,3,h,w,nhwc)*stride;
            float x1=std::max(0.f,(x+0.5f)*stride-left);
            float y1=std::max(0.f,(y+0.5f)*stride-top);
            float x2=std::min(static_cast<float>(kSize),(x+0.5f)*stride+right);
            float y2=std::min(static_cast<float>(kSize),(y+0.5f)*stride+bottom);
            Face face={x1,y1,x2-x1,y2-y1,score};
            if(face.w<=0 || face.h<=0) continue;
            if(count<kMaxCandidates) candidates[count++]=face;
            else {
                int worst=0;
                for(int i=1;i<count;++i) if(candidates[i].score<candidates[worst].score) worst=i;
                if(score>candidates[worst].score) candidates[worst]=face;
            }
        }
    }
    std::sort(candidates,candidates+count,[](const Face& a,const Face& b){ return a.score>b.score; });
    result.count=0;
    for(int i=0;i<count && result.count<kMaxFaces;++i) {
        bool suppressed=false;
        for(int j=0;j<result.count;++j) if(iou(candidates[i],result.faces[j])>0.45f) suppressed=true;
        if(!suppressed) result.faces[result.count++]=candidates[i];
    }
    for(int i=0;i<result.count;++i) {
        if(kRotateClockwise) {
            Face& face=result.faces[i];
            float x=face.y, y=kSize-face.x-face.w;
            float w=face.h, h=face.w;
            face.x=x; face.y=y; face.w=w; face.h=h;
        }
        result.faces[i].x*=static_cast<float>(result.width)/kSize;
        result.faces[i].w*=static_cast<float>(result.width)/kSize;
        result.faces[i].y*=static_cast<float>(result.height)/kSize;
        result.faces[i].h*=static_cast<float>(result.height)/kSize;
    }
    return true;
}
void rotate_rgb_clockwise(uint8_t* data) {
    // Transpose, then reverse each row; no second image buffer is required.
    for(int y=0;y<kSize;++y) for(int x=y+1;x<kSize;++x)
        for(int c=0;c<3;++c) std::swap(data[(y*kSize+x)*3+c],data[(x*kSize+y)*3+c]);
    for(int y=0;y<kSize;++y) for(int x=0;x<kSize/2;++x)
        for(int c=0;c<3;++c) std::swap(data[(y*kSize+x)*3+c],data[(y*kSize+kSize-1-x)*3+c]);
}
}

int cv_yolov8n_ob_init(bool security,bool privilege,uint32_t model_addr) {
    xprintf("OPEN_FACE_V1 independent yolov8n-face raw-heads 192\r\n");
    const volatile uint8_t* model_bytes=(const volatile uint8_t*)model_addr;
    uint32_t checksum=2166136261u;
    for(uint32_t i=0;i<FACE_MODEL_BYTES;++i) checksum=(checksum^model_bytes[i])*16777619u;
    xprintf("FACE_MODEL bytes=%d checksum=%x expected=%x\r\n",FACE_MODEL_BYTES,checksum,FACE_MODEL_FNV);
    if(checksum!=FACE_MODEL_FNV) { xprintf("FACE_ERROR model incomplete\r\n"); return -1; }
    uint32_t arena=mm_reserve_align(kArenaBytes,32);
    if(!arena) { xprintf("FACE_ERROR arena allocation\r\n"); published.state=2; return -1; }
    EPII_NVIC_SetVector((IRQn_Type)U55_IRQn,(uint32_t)npu_irq); NVIC_EnableIRQ((IRQn_Type)U55_IRQn);
    xprintf("FACE_INIT npu\r\n");
    if(ethosu_init(&npu,(void*)BASE_ADDR_APB_U55_CTRL_ALIAS,nullptr,0,security,privilege)) return -1;
    const tflite::Model* model=tflite::GetModel((void*)model_addr);
    if(model->version()!=TFLITE_SCHEMA_VERSION) return -1;
    static tflite::MicroMutableOpResolver<3> resolver;
    resolver.AddEthosU(); resolver.AddTranspose(); resolver.AddReshape();
    static tflite::MicroInterpreter instance(model,resolver,(uint8_t*)arena,kArenaBytes);
    xprintf("FACE_INIT tensors\r\n");
    if(instance.AllocateTensors()!=kTfLiteOk) { published.state=2; return -1; }
    interpreter=&instance; input=instance.input(0);
    if(input->type!=kTfLiteInt8 || input->dims->size!=4 || input->bytes!=kSize*kSize*3 || instance.outputs_size()!=3) {
        xprintf("FACE_ERROR unexpected model tensors\r\n"); published.state=2; interpreter=nullptr; return -1;
    }
    xprintf("FACE_READY arena_used=%d input_scale_x1e6=%d zero=%d\r\n",instance.arena_used_bytes(),(int)(input->params.scale*1000000),input->params.zero_point);
    for(int i=0;i<3;++i) {
        auto* out=instance.output(i);
        xprintf("HEAD %d dims=%d,%d,%d,%d scale_x1e6=%d zero=%d\r\n",i,out->dims->data[0],out->dims->data[1],out->dims->data[2],out->dims->data[3],(int)(out->params.scale*1000000),out->params.zero_point);
    }
    xprintf("FACE_INIT i2c\r\n");
    init_i2c();
    xprintf("FACE_INIT done\r\n");
    return 0;
}
int cv_yolov8n_ob_run(struct_yolov8_ob_algoResult*) {
    if(!interpreter) return -1;
    uint32_t width=app_get_raw_width(),height=app_get_raw_height();
    hx_lib_image_resize_BGR8U3C_to_RGB24_helium((uint8_t*)app_get_raw_addr(),(uint8_t*)input->data.data,
        width,height,app_get_raw_channels(),kSize,kSize,(float)(width-1)/(kSize-1),(float)(height-1)/(kSize-1));
    if(kRotateClockwise) rotate_rgb_clockwise((uint8_t*)input->data.data);
#ifdef FACE_DUMP_INPUT
    if(frame==8) {
        xprintf("DEBUG_RGB_BEGIN\r\n");
        const char hex[]="0123456789abcdef";
        for(int offset=0;offset<input->bytes;offset+=192) {
            char line[385];
            for(int i=0;i<192;++i) {
                uint8_t value=((uint8_t*)input->data.data)[offset+i];
                line[i*2]=hex[value>>4]; line[i*2+1]=hex[value&15];
            }
            line[384]=0; xprintf("%s\r\n",line);
        }
        xprintf("DEBUG_RGB_END\r\n");
    }
#endif
    for(int i=0;i<input->bytes;++i) {
        uint8_t pixel=((uint8_t*)input->data.data)[i];
        int value=(int)std::round((pixel/255.f)/input->params.scale)+input->params.zero_point;
        input->data.int8[i]=(int8_t)std::max(-128,std::min(127,value));
    }
    Result result={}; result.width=width; result.height=height; result.frame=++frame;
    result.state=(interpreter->Invoke()==kTfLiteOk && decode(result)) ? 1 : 2;
    uint32_t irq=__get_PRIMASK(); __disable_irq(); published=result; __set_PRIMASK(irq);
    xprintf("FACE_FRAME %d %d %d %d state=%d\r\n",result.frame,result.count,width,height,result.state);
    for(int i=0;i<result.count;++i) {
        const Face& f=result.faces[i];
        xprintf("FACE_BOX %d %d %d %d %d %d %d\r\n",result.frame,i,(int)f.x,(int)f.y,(int)f.w,(int)f.h,(int)(f.score*100));
    }
    sensordplib_retrigger_capture();
    return result.state==1 ? 0 : -1;
}
int cv_yolov8n_ob_deinit() { return 0; }
