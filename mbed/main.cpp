// Importing the necessary header files for mbed OS, KW40z, OLED screen and 
// FXOS 8700
#include "mbed.h"
#include "mbed_events.h"
#include "Hexi_KW40Z.h"
#include "Hexi_OLED_SSD1351.h"
#include "OLED_types.h"
#include "OpenSans_Font.h"
#include "string.h"
#include "FXOS8700.h"


// Utility functions defined below
void StartHaptic(void);
void StopHaptic(void const *n);
float Filter(int s);
void AlertReceived(uint8_t *data, uint8_t length);
void clearScreen();

void displayString();
void UpdateSensorData(void);
void BTTask(void);
void dataTask(void);

void ButtonLeft();
void ButtonRight();
void ButtonDown();
void ButtonUp();
void ButtonLeft(void);

/* Instantiate the accelerometer */ 

FXOS8700 accel(PTC11, PTC10);

/* Instantiate the Hexi KW40Z Driver (UART TX, UART RX) */ 
KW40Z kw40z_device(PTE24, PTE25);

/* Instantiate the SSD1351 OLED Driver */ 
SSD1351 oled(PTB22,PTB21,PTC13,PTB20,PTE6, PTD15);

RtosTimer hapticTimer(StopHaptic, osTimerOnce);
DigitalOut haptic(PTB9);

/* Create a Thread to handle sending BLE Sensor Data */ 
Thread bluetoothThread;
Thread dataThread;

/* Create a Thread to handle displaying */ 
Thread displayThread;
EventQueue displayEventQueue;

char text[20]; 

// Variables
float accel_data[3]; // Storage for the data from the sensor
float accel_rms=0.0; // RMS value from the sensor
float ax, ay, az; // Integer value from the sensor to be displayed
const uint8_t *image1; // Pointer for the image1 to be displayed
char text1[20]; // Text Buffer for dynamic value displayed
char text2[20]; // Text Buffer for dynamic value displayed
char text3[20]; // Text Buffer for dynamic value displayed
float dot;
float old_acc=0;
float new_acc=0;
float old_accx, old_accy, old_accz, old_dot=0.0;
uint8_t StepNum = 0, StepNumber = 0;

// Buffer for averaging out the Pedometer data
float filter_buf[75];

uint8_t result[1]={0};


// variable to assist with viewing the other users' data
char user[2]; 
char mean[4];
char max[4];
char min[4];
char steps[6];
// boolean flag that says whether or not we've processed new data from pi
// default to true because not data from pi until we ask for it
bool processedReceivedData = true;

int flag = 0;
int userChosen = flag;

// main() runs in its own thread in the OS
int main() {
    
    /* Attaching the different functions to the Haptic Buttons*/
    kw40z_device.attach_buttonLeft(&ButtonLeft);
    kw40z_device.attach_buttonRight(&ButtonRight);
    kw40z_device.attach_buttonDown(&ButtonDown);
    kw40z_device.attach_buttonUp(&ButtonUp);
    kw40z_device.attach_alert(&AlertReceived);
    
    /* Starting the accelerometer values*/
    accel.accel_config();
    
    // open up the display queue so that at any point in the program,
    // we can put things inside of it and they'll be executed eventually
    displayThread.start(callback(&displayEventQueue, &EventQueue::dispatch_forever));
    displayEventQueue.call(&clearScreen);
    
    /*Thread start the thread for Handling Bluetooth Events*/
    dataThread.start(BTTask);
    bluetoothThread.start(dataTask);
    
    wait(osWaitForever); 
}

// Function for handling Bluetooth toggling advertisement, send Alert flag and 
// Step numbers
void BTTask(void){
   
   while (true) 
   {
        if (kw40z_device.GetLinkState() == 0) {
            kw40z_device.ToggleAdvertisementMode();
         }
        
        /*Notify Hexiwear App that it is running Sensor Tag mode*/
        kw40z_device.SendSetApplicationMode(GUI_CURRENT_APP_SENSOR_TAG);
        
        kw40z_device.SendAlert(result, 2);
        kw40z_device.SendBatteryLevel(StepNumber);

        Thread::wait(1000);                 
    }
}

// Function for setting up the flag to configure different users to different
// buttons on the Hexiwear and also to compute Pedometer algorithm based on 
// Hexiwear data
void dataTask(void) {    
    while (true) {
        if(flag == 1) {
            result[1] = 1;
            flag = 0;
            userChosen = 1;
        }
        
        if(flag == 2) { 
            result[1] = 2;
            flag = 0;
            userChosen = 2;
        }
        
        if(flag == 3){ 
            result[1] = 3;
            flag = 0;
            userChosen = 3;
        }
        
        accel.acquire_accel_data_g(accel_data);
        ax = Filter(0);
        ay = Filter(1);
        az = Filter(2);  
        wait(0.02);           
        accel_rms = sqrt((ax*ax)+(ay*ay)+(az*az)/3);
        dot = (old_accx * ax)+(old_accy * ay)+(old_accz * az);
        old_acc = abs(sqrt(old_accx*old_accx+old_accy*old_accy+old_accz*old_accz));
        new_acc = abs(sqrt(ax*ax+ay*ay+az*az));
        dot /= (old_acc * new_acc);
        
        /* Display Legends */ 
        StepNum = StepNumber;
        if(abs(dot - old_dot) >= 0.05 && abs(dot - old_dot) <= 0.10) {
            StepNumber += 1;
        }
        
        old_accx = ax;
        old_accy = ay;
        old_accz = az;
        old_dot = dot;
        
        Thread::wait(250);
    }
}

void StartHaptic(void)  {
    hapticTimer.start(50);
    haptic = 1;
}

void StopHaptic(void const *n) {
    haptic = 0;
    hapticTimer.stop();
}

float Filter(int s) {
    accel.acquire_accel_data_g(accel_data);
    float filter_sum = 0.0;
    //printf("%d\n\r",s);
    for(int i = 0; i < 75; i++) 
    {
    filter_buf[i] = accel_data[s];
    //printf("%4.2f\n\r",filter_buf[i]);
    filter_sum += filter_buf[i];
    }
    return (float)(filter_sum / 75);
}

// Key modification: use the alert functionality enabled by the host-ble interface
// to define our own command to display different user's data
void AlertReceived(uint8_t *data, uint8_t length) {
    processedReceivedData = false;
    
    StartHaptic();
    data[19] = 0;
    
    user[0] = '0' + userChosen;
    
    mean[0] = data[0];
    mean[1] = data[1];
    mean[2] = data[2];
    
    max[0] = data[5];
    max[1] = data[6];
    max[2] = data[7];
    
    min[0] = data[10];
    min[1] = data[11];
    min[2] = data[12];
    
    steps[0] = data[15];
    steps[1] = data[16];
    steps[2] = data[17];
    steps[3] = data[18];
    steps[4] = data[19];
    
    user[1] = 0;
    mean[3] = 0;
    max[3] = 0;
    min[3] = 0;
    steps[5] = 0;
    
    // if you haven't yet processed the data that pi sent
    // you in the past, then don't do anything.
    
    // 2: queue up the displaying of that string
    displayEventQueue.call(&displayString);
}


/****************************Call Back Functions*******************************/

// just write the received data to the screen
void displayString() {
    if (!processedReceivedData) {
        clearScreen();
        
        processedReceivedData = true;
        oled_text_properties_t textProperties = {0};
        oled.GetTextProperties(&textProperties);
        
        textProperties.fontColor   = COLOR_BLUE;
        oled.SetTextProperties(&textProperties);
        
        sprintf(text, "USER: %s\0",user);
        oled.Label((uint8_t*)text,0,0);
        
        sprintf(text, "MEAN HR: %s\0",mean);
        oled.Label((uint8_t*)text,0,15);
        
        sprintf(text, "MAX HR: %s\0",max);
        oled.Label((uint8_t*)text,0,30);
        
        sprintf(text, "MIN HR: %s\0",min);
        oled.Label((uint8_t*)text,0,45);
        
        sprintf(text, "STEPS: %s\0",steps);
        oled.Label((uint8_t*)text,0,60);
    }
}

void ButtonUp(void) {
    StartHaptic();
    flag = 1;
//    processedReceivedData = false;
}

void ButtonDown(void) {
    StartHaptic();
    flag = 2;
//    processedReceivedData = false;
}

void ButtonRight(void) {
    StartHaptic();
    flag = 3;
//    processedReceivedData = false;
}

void ButtonLeft(void) {
    StartHaptic();
    kw40z_device.ToggleAdvertisementMode();
}



// initialize the screen to black
void clearScreen() {    
    oled.FillScreen(COLOR_BLACK);
}