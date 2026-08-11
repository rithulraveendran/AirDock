import cv2 
import mediapipe as mp 
from mediapipe .tasks import python as mp_python 
from mediapipe .tasks .python import vision 
import pyautogui 
import pystray 
from PIL import Image ,ImageDraw ,ImageFont ,ImageTk 
import numpy as np 
import threading 
import queue 
import time 
import json 
import os 
import winreg 
import sys 
import urllib .request 
from collections import deque 
import customtkinter as ctk 
import pywinstyles 

CONFIG_FILE ="config.json"
MODEL_FILE ="hand_landmarker.task"
MODEL_URL ="https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"


HAND_CONNECTIONS =[
(0 ,1 ),(1 ,2 ),(2 ,3 ),(3 ,4 ),
(0 ,5 ),(5 ,6 ),(6 ,7 ),(7 ,8 ),
(5 ,9 ),(9 ,10 ),(10 ,11 ),(11 ,12 ),
(9 ,13 ),(13 ,14 ),(14 ,15 ),(15 ,16 ),
(13 ,17 ),(0 ,17 ),(17 ,18 ),(18 ,19 ),(19 ,20 )
]

DEFAULT_CONFIG ={
"enabled":True ,
"show_window_on_start":True ,
"cooldown_seconds":1.2 ,
"swipe_threshold_x":0.12 ,
"swipe_threshold_y":0.10 ,
"fist_ratio_threshold":1.25 ,
"fist_hold_seconds":0.5 ,
"camera_index":0 ,
"startup_registered":False ,
"always_on_top":True ,
"volume_steps_per_swipe":5 ,
"minimize_on_close":True ,

"hotkey_swipe_right":["alt","tab"],
"hotkey_swipe_left":["alt","shift","tab"],
"hotkey_swipe_up":["volumeup"],
"hotkey_swipe_down":["volumedown"],
"hotkey_fist":["printscreen"],


"color_joint_active":[255 ,0 ,255 ],
"color_line_active":[255 ,255 ,0 ],
"color_joint_paused":[0 ,0 ,255 ],
"color_line_paused":[128 ,128 ,128 ]
}

def get_resource_path (relative_path ):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try :

        base_path =sys ._MEIPASS 
    except Exception :
        base_path =os .path .abspath (".")
    return os .path .join (base_path ,relative_path )

def load_config ():
    if not os .path .exists (CONFIG_FILE ):
        with open (CONFIG_FILE ,'w')as f :
            json .dump (DEFAULT_CONFIG ,f ,indent =4 )
        return DEFAULT_CONFIG .copy ()
    try :
        with open (CONFIG_FILE ,'r')as f :
            config =json .load (f )


            if config .get ("hotkey_swipe_right")==["ctrl","tab"]:
                config ["hotkey_swipe_right"]=["alt","tab"]
            if config .get ("hotkey_swipe_left")==["ctrl","shift","tab"]:
                config ["hotkey_swipe_left"]=["alt","shift","tab"]


            if config .get ("fist_ratio_threshold",1.25 )<1.0 :
                config ["fist_ratio_threshold"]=1.25 


            for k ,v in DEFAULT_CONFIG .items ():
                if k not in config :
                    config [k ]=v 
            return config 
    except Exception as e :
        print (f"Error loading config: {e }")
        return DEFAULT_CONFIG .copy ()

def save_config (config ):
    try :
        with open (CONFIG_FILE ,'w')as f :
            json .dump (config ,f ,indent =4 )
    except Exception as e :
        print (f"Error saving config: {e }")

def ensure_model_exists ():
    model_path =get_resource_path (MODEL_FILE )
    if not os .path .exists (model_path ):
        print (f"Downloading model file to {model_path }...")

        urllib .request .urlretrieve (MODEL_URL ,MODEL_FILE )
        print ("Model downloaded.")

class GestureController :
    def __init__ (self ,gui_callback =None ):
        self .config =load_config ()
        save_config (self .config )

        self .running =threading .Event ()
        self .running .set ()

        self .enabled =self .config ["enabled"]
        self .gui_callback =gui_callback 

        self .swipe_buffer =deque (maxlen =30 )
        self .trail_buffer =deque (maxlen =15 )

        self .last_action_time =0 
        self .fist_start_time =None 
        self .hand_lost_frames =0 

        self .volume_hold_active =False 
        self .volume_hold_direction =None 
        self .last_volume_step_time =0 

        self .last_triggered_action =""
        self .last_triggered_time =0 

        self .left_hand_action_done =False 
        self .right_hand_action_done =False 

        self .current_dx =0.0 
        self .current_dy =0.0 
        self .current_fist_ratio =2.0 
        self .fps =0 
        self .alt_held =False 

        pyautogui .PAUSE =0 
        pyautogui .FAILSAFE =False 

        self .capture_thread =None 

    def start (self ):
        self .running .set ()
        self .capture_thread =threading .Thread (target =self .capture_thread_wrapper ,daemon =True )
        self .capture_thread .start ()

    def capture_thread_wrapper (self ):
        try :
            self .capture_thread_func ()
        except Exception as e :
            import traceback 
            import tkinter .messagebox as messagebox 
            log_dir =os .path .dirname (os .path .abspath (sys .argv [0 ]))
            log_file =os .path .join (log_dir ,"airdock_error.log")
            err_msg =f"Exception in capture thread: {e }\n\n{traceback .format_exc ()}"
            try :
                with open (log_file ,"w")as f :
                    f .write (err_msg )
            except :
                pass 
            messagebox .showerror ("Gesture Controller Error",f"The background gesture processor failed:\n\n{e }\n\nCheck 'airdock_error.log' for details.")

    def stop (self ):
        self .running .clear ()
        if getattr (self ,'alt_held',False ):
            try :
                pyautogui .keyUp ('alt')
            except :
                pass 
            self .alt_held =False 
        if self .capture_thread :
            self .capture_thread .join (timeout =2.0 )

    def draw_landmarks (self ,frame ,landmarks ):
        h ,w ,_ =frame .shape 

        if self .enabled :
            joint_color =tuple (self .config ["color_joint_active"])
            line_color =tuple (self .config ["color_line_active"])
        else :
            joint_color =tuple (self .config ["color_joint_paused"])
            line_color =tuple (self .config ["color_line_paused"])

        for connection in HAND_CONNECTIONS :
            idx1 ,idx2 =connection 
            lm1 =landmarks [idx1 ]
            lm2 =landmarks [idx2 ]
            cx1 ,cy1 =int (lm1 .x *w ),int (lm1 .y *h )
            cx2 ,cy2 =int (lm2 .x *w ),int (lm2 .y *h )
            cv2 .line (frame ,(cx1 ,cy1 ),(cx2 ,cy2 ),line_color ,2 )

        for lm in landmarks :
            cx ,cy =int (lm .x *w ),int (lm .y *h )
            cv2 .circle (frame ,(cx ,cy ),6 ,joint_color ,cv2 .FILLED )
            cv2 .circle (frame ,(cx ,cy ),8 ,(255 ,255 ,255 ),1 )

        for i in range (1 ,len (self .trail_buffer )):
            pt1 =self .trail_buffer [i -1 ]
            pt2 =self .trail_buffer [i ]
            alpha =i /len (self .trail_buffer )
            tc =(int (255 *alpha ),int (255 *alpha ),0 )
            thickness =int (1 +alpha *4 )
            cv2 .line (frame ,pt1 ,pt2 ,tc ,thickness )

    def get_hand_features (self ,landmarks ):
        wrist =landmarks [0 ]
        middle_mcp =landmarks [9 ]

        palm_size =((wrist .x -middle_mcp .x )**2 +(wrist .y -middle_mcp .y )**2 +(wrist .z -middle_mcp .z )**2 )**0.5 
        if palm_size ==0 :
            palm_size =0.001 

        tips =[8 ,12 ,16 ,20 ]
        total_tip_dist =0 
        for tip_idx in tips :
            tip =landmarks [tip_idx ]
            dist =((wrist .x -tip .x )**2 +(wrist .y -tip .y )**2 +(wrist .z -tip .z )**2 )**0.5 
            total_tip_dist +=dist 

        avg_tip_dist =total_tip_dist /4.0 
        fist_ratio =avg_tip_dist /palm_size 
        return middle_mcp .x ,middle_mcp .y ,fist_ratio 

    def robust_hotkey (self ,keys ):
        try :
            is_complex =any (k in keys for k in ["alt","ctrl","shift"])
            hold_time =0.08 if is_complex else 0.02 

            is_volume =any (k in ["volumeup","volumedown"]for k in keys )
            loops =self .config .get ("volume_steps_per_swipe",5 )if is_volume else 1 

            for _ in range (loops ):
                for key in keys :
                    pyautogui .keyDown (key )
                    time .sleep (hold_time )
                for key in reversed (keys ):
                    pyautogui .keyUp (key )
                    time .sleep (hold_time )
                if is_volume :
                    time .sleep (0.02 )
        except Exception as e :
            print (f"Error simulating robust hotkey: {e }")

    def trigger_action (self ,action_name ,keys ,now ,custom_cooldown =None ):
        cooldown =custom_cooldown if custom_cooldown is not None else self .config ["cooldown_seconds"]
        if now -self .last_action_time >cooldown :
            self .last_triggered_action =action_name 
            self .last_triggered_time =now 
            self .last_action_time =now 

            t =threading .Thread (target =self .robust_hotkey ,args =(keys ,),daemon =True )
            t .start ()

            print (f"Triggered Action: {action_name } ({keys })")
            self .swipe_buffer .clear ()

    def trigger_app_switch (self ,direction ,now ):
        cooldown =0.4 
        if now -self .last_action_time >cooldown :
            self .last_triggered_action ="Next App"if direction =="next"else "Prev App"
            self .last_triggered_time =now 
            self .last_action_time =now 

            t =threading .Thread (target =self .do_app_switch ,args =(direction ,),daemon =True )
            t .start ()

            self .swipe_buffer .clear ()

    def do_app_switch (self ,direction ):
        try :
            if not getattr (self ,'alt_held',False ):
                pyautogui .keyDown ('alt')
                self .alt_held =True 
                time .sleep (0.05 )

            if direction =="next":
                pyautogui .press ('tab')
            else :
                pyautogui .keyDown ('shift')
                pyautogui .press ('tab')
                pyautogui .keyUp ('shift')
        except Exception as e :
            print (f"Error in do_app_switch: {e }")

    def capture_thread_func (self ):
        ensure_model_exists ()
        model_path =get_resource_path (MODEL_FILE )

        base_options =mp_python .BaseOptions (model_asset_path =model_path )
        options =vision .HandLandmarkerOptions (base_options =base_options ,num_hands =1 )
        detector =vision .HandLandmarker .create_from_options (options )

        cap =cv2 .VideoCapture (self .config ["camera_index"],cv2 .CAP_DSHOW )
        if not cap .isOpened ():
            raise Exception (f"Failed to open webcam at index {self .config ['camera_index']}. Make sure your camera is connected and not in use by another app.")
        cap .set (cv2 .CAP_PROP_FRAME_WIDTH ,640 )
        cap .set (cv2 .CAP_PROP_FRAME_HEIGHT ,480 )

        last_fps_time =time .time ()
        fps_frames =0 

        print ("Capture thread started.")
        while self .running .is_set ():
            ret ,frame =cap .read ()
            if not ret :
                time .sleep (0.03 )
                continue 

            frame =cv2 .flip (frame ,1 )

            fps_frames +=1 
            now =time .time ()
            if now -last_fps_time >=1.0 :
                self .fps =fps_frames 
                fps_frames =0 
                last_fps_time =now 

            if not self .enabled :
                self .trail_buffer .clear ()
                self .volume_hold_active =False 
                if getattr (self ,'alt_held',False ):
                    try :
                        pyautogui .keyUp ('alt')
                    except :
                        pass 
                    self .alt_held =False 
                if self .gui_callback :
                    self .gui_callback (frame ,None ,"PAUSED")
                time .sleep (0.03 )
                continue 


            if getattr (self ,'alt_held',False )and (now -self .last_action_time >2.0 ):
                try :
                    pyautogui .keyUp ('alt')
                except :
                    pass 
                self .alt_held =False 
                print ("Released ALT due to timeout")

            rgb_frame =cv2 .cvtColor (frame ,cv2 .COLOR_BGR2RGB )
            mp_image =mp .Image (image_format =mp .ImageFormat .SRGB ,data =rgb_frame )
            detection_result =detector .detect (mp_image )

            current_gesture =""
            in_cooldown =(now -self .last_action_time <self .config ["cooldown_seconds"])

            if detection_result .hand_landmarks :
                self .hand_lost_frames =0 
                hand_landmarks =detection_result .hand_landmarks [0 ]

                h ,w ,_ =frame .shape 
                mx ,my =int (hand_landmarks [9 ].x *w ),int (hand_landmarks [9 ].y *h )
                self .trail_buffer .append ((mx ,my ))

                self .draw_landmarks (frame ,hand_landmarks )

                x ,y ,fist_ratio =self .get_hand_features (hand_landmarks )
                self .current_fist_ratio =fist_ratio 


                hand_label ="Right"
                if detection_result .handedness :
                    hand_info =detection_result .handedness [0 ]
                    if hand_info :
                        category =hand_info [0 ]
                        hand_label =getattr (category ,'category_name',getattr (category ,'label','Right'))


                if self .volume_hold_active :
                    if self .volume_hold_direction =="up"and (y >0.40 or hand_label !="Right"):
                        self .volume_hold_active =False 
                        self .last_action_time =now 
                    elif self .volume_hold_direction =="down"and (y <0.60 or hand_label !="Left"):
                        self .volume_hold_active =False 
                        self .last_action_time =now 
                    else :
                        current_gesture =f"VOLUME {self .volume_hold_direction .upper ()} (HOLD)"
                        if now -self .last_volume_step_time >0.10 :
                            pyautogui .press ("volumeup"if self .volume_hold_direction =="up"else "volumedown")
                            self .last_volume_step_time =now 
                            self .last_action_time =now 
                else :

                    if fist_ratio <self .config ["fist_ratio_threshold"]:
                        if self .fist_start_time is None :
                            self .fist_start_time =now 
                        elif now -self .fist_start_time >self .config ["fist_hold_seconds"]:
                            self .trigger_action ("Screenshot",self .config ["hotkey_fist"],now )
                            self .fist_start_time =None 
                        current_gesture ="FIST (Holding...)"
                    else :
                        self .fist_start_time =None 

                        if in_cooldown :
                            self .swipe_buffer .clear ()
                            self .current_dx =0.0 
                            self .current_dy =0.0 
                        else :
                            self .swipe_buffer .append ((x ,y ,now ))

                            ref_x ,ref_y =None ,None 
                            for px ,py ,pt in self .swipe_buffer :
                                if 0.15 <=(now -pt )<=0.45 :
                                    ref_x ,ref_y =px ,py 
                                    break 

                            if ref_x is not None :
                                dx =x -ref_x 
                                dy =y -ref_y 
                                self .current_dx =dx 
                                self .current_dy =dy 

                                abs_dx =abs (dx )
                                abs_dy =abs (dy )

                                thresh_x =self .config ["swipe_threshold_x"]
                                thresh_y =self .config ["swipe_threshold_y"]

                                if abs_dx >thresh_x or abs_dy >thresh_y :
                                    if abs_dx >abs_dy *1.3 :
                                        if abs_dx >thresh_x :
                                            if dx >0 :
                                                current_gesture ="SWIPE RIGHT"
                                                self .trigger_app_switch ("next",now )
                                            else :
                                                current_gesture ="SWIPE LEFT"
                                                self .trigger_app_switch ("prev",now )
                                    elif abs_dy >abs_dx *1.3 :
                                        if abs_dy >thresh_y :

                                            if hand_label =="Left":
                                                current_gesture ="SWIPE (VOLUME DOWN)"
                                                pyautogui .press ('volumedown',presses =5 )
                                                self .last_action_time =now 
                                                self .volume_hold_active =True 
                                                self .volume_hold_direction ="down"
                                                self .last_volume_step_time =now 
                                            else :
                                                current_gesture ="SWIPE (VOLUME UP)"
                                                pyautogui .press ('volumeup',presses =5 )
                                                self .last_action_time =now 
                                                self .volume_hold_active =True 
                                                self .volume_hold_direction ="up"
                                                self .last_volume_step_time =now 
            else :
                self .hand_lost_frames +=1 
                if self .hand_lost_frames >8 :
                    self .trail_buffer .clear ()
                    self .swipe_buffer .clear ()
                    self .volume_hold_active =False 
                    self .left_hand_action_done =False 
                    self .right_hand_action_done =False 
                    self .current_dx =0.0 
                    self .current_dy =0.0 
                    self .current_fist_ratio =2.0 
                    if getattr (self ,'alt_held',False ):
                        try :
                            pyautogui .keyUp ('alt')
                        except :
                            pass 
                        self .alt_held =False 

            if self .gui_callback :
                self .gui_callback (frame ,current_gesture ,"ACTIVE")

        cap .release ()
        print ("Capture thread stopped.")


class PremiumApp (ctk .CTk ):
    def __init__ (self ):
        super ().__init__ ()


        self .config =load_config ()
        self .enabled_state =self .config ["enabled"]
        self .always_on_top_state =self .config ["always_on_top"]
        self .minimize_on_close_state =self .config ["minimize_on_close"]


        self .queue =queue .Queue (maxsize =1 )
        self .controller =GestureController (gui_callback =self .on_frame_processed )
        self .controller .start ()


        self .title ("Gesture Control Center")
        self .geometry ("820x540")
        self .resizable (False ,False )


        ctk .set_appearance_mode ("dark")
        ctk .set_default_color_theme ("blue")


        pywinstyles .apply_style (self ,"acrylic")
        pywinstyles .change_header_color (self ,"#16181C")
        pywinstyles .change_border_color (self ,"#2C3E50")


        self .grid_rowconfigure (0 ,weight =1 )
        self .grid_columnconfigure (1 ,weight =1 )


        self .sidebar_frame =ctk .CTkFrame (self ,width =170 ,corner_radius =0 ,fg_color ="#111317")
        self .sidebar_frame .grid (row =0 ,column =0 ,sticky ="nsew")
        self .sidebar_frame .grid_rowconfigure (4 ,weight =1 )


        self .logo_label =ctk .CTkLabel (self .sidebar_frame ,text ="AirDock",font =ctk .CTkFont (family ="Segoe UI",size =20 ,weight ="bold"),text_color ="#00f0ff")
        self .logo_label .grid (row =0 ,column =0 ,padx =20 ,pady =25 )


        self .btn_dashboard =ctk .CTkButton (self .sidebar_frame ,text ="🏠  Dashboard",anchor ="w",fg_color ="#1F2630",hover_color ="#2A3545",command =self .show_dashboard )
        self .btn_dashboard .grid (row =1 ,column =0 ,padx =15 ,pady =8 ,sticky ="ew")

        self .btn_settings =ctk .CTkButton (self .sidebar_frame ,text ="⚙️  Settings",anchor ="w",fg_color ="transparent",hover_color ="#2A3545",command =self .show_settings )
        self .btn_settings .grid (row =2 ,column =0 ,padx =15 ,pady =8 ,sticky ="ew")

        self .btn_help =ctk .CTkButton (self .sidebar_frame ,text ="ℹ️  Help Guide",anchor ="w",fg_color ="transparent",hover_color ="#2A3545",command =self .show_help )
        self .btn_help .grid (row =3 ,column =0 ,padx =15 ,pady =8 ,sticky ="ew")


        self .sidebar_toggle =ctk .CTkSwitch (self .sidebar_frame ,text ="Active",progress_color ="#00f0ff",command =self .toggle_active_state )
        if self .enabled_state :
            self .sidebar_toggle .select ()
        self .sidebar_toggle .grid (row =5 ,column =0 ,padx =20 ,pady =25 ,sticky ="s")


        self .main_frame =ctk .CTkFrame (self ,corner_radius =0 ,fg_color ="transparent")
        self .main_frame .grid (row =0 ,column =1 ,sticky ="nsew",padx =20 ,pady =20 )
        self .main_frame .grid_rowconfigure (0 ,weight =1 )
        self .main_frame .grid_columnconfigure (0 ,weight =1 )


        self .pages ={}
        self .create_pages ()
        self .show_dashboard ()


        self .tray_icon =None 
        self .setup_system_tray ()


        self .protocol ("WM_DELETE_WINDOW",self .on_window_close )


        self .apply_always_on_top ()


        self .poll_queue ()

    def create_pages (self ):

        dash_page =ctk .CTkFrame (self .main_frame ,fg_color ="transparent")
        dash_page .grid_columnconfigure (0 ,weight =3 )
        dash_page .grid_columnconfigure (1 ,weight =2 )
        dash_page .grid_rowconfigure (0 ,weight =1 )


        webcam_card =ctk .CTkFrame (dash_page ,fg_color ="#181B22",border_width =1 ,border_color ="#2C3E50")
        webcam_card .grid (row =0 ,column =0 ,padx =(0 ,10 ),pady =0 ,sticky ="nsew")

        self .canvas =ctk .CTkLabel (webcam_card ,text ="",width =380 ,height =285 )
        self .canvas .pack (padx =15 ,pady =15 ,fill ="both",expand =True )


        diag_card =ctk .CTkFrame (dash_page ,fg_color ="#181B22",border_width =1 ,border_color ="#2C3E50")
        diag_card .grid (row =0 ,column =1 ,padx =(10 ,0 ),pady =0 ,sticky ="nsew")

        lbl_diag =ctk .CTkLabel (diag_card ,text ="Diagnostics",font =ctk .CTkFont (family ="Segoe UI",size =16 ,weight ="bold"),text_color ="#00f0ff")
        lbl_diag .pack (padx =15 ,pady =(15 ,10 ),anchor ="w")


        self .lbl_status =ctk .CTkLabel (diag_card ,text ="Status: ACTIVE",font =ctk .CTkFont (family ="Segoe UI",size =14 ,weight ="bold"),text_color ="#2ECC71")
        self .lbl_status .pack (padx =15 ,pady =5 ,anchor ="w")


        self .lbl_fps =ctk .CTkLabel (diag_card ,text ="FPS: 0",font =ctk .CTkFont (family ="Segoe UI",size =13 ))
        self .lbl_fps .pack (padx =15 ,pady =2 ,anchor ="w")


        self .lbl_dx =ctk .CTkLabel (diag_card ,text ="Move X: 0.00 / 0.12",font =ctk .CTkFont (family ="Segoe UI",size =12 ))
        self .lbl_dx .pack (padx =15 ,pady =(10 ,0 ),anchor ="w")
        self .bar_dx =ctk .CTkProgressBar (diag_card ,progress_color ="#00f0ff")
        self .bar_dx .set (0.5 )
        self .bar_dx .pack (padx =15 ,pady =5 ,fill ="x")


        self .lbl_dy =ctk .CTkLabel (diag_card ,text ="Move Y: 0.00 / 0.10",font =ctk .CTkFont (family ="Segoe UI",size =12 ))
        self .lbl_dy .pack (padx =15 ,pady =(10 ,0 ),anchor ="w")
        self .bar_dy =ctk .CTkProgressBar (diag_card ,progress_color ="#ff00ff")
        self .bar_dy .set (0.5 )
        self .bar_dy .pack (padx =15 ,pady =5 ,fill ="x")


        self .lbl_fist =ctk .CTkLabel (diag_card ,text ="Fist Ratio: 2.00 / 1.25",font =ctk .CTkFont (family ="Segoe UI",size =12 ))
        self .lbl_fist .pack (padx =15 ,pady =(10 ,0 ),anchor ="w")
        self .bar_fist =ctk .CTkProgressBar (diag_card ,progress_color ="#E74C3C")
        self .bar_fist .set (1.0 )
        self .bar_fist .pack (padx =15 ,pady =5 ,fill ="x")


        trigger_card =ctk .CTkFrame (diag_card ,fg_color ="#13171F",height =80 )
        trigger_card .pack (padx =15 ,pady =(20 ,15 ),fill ="x")

        self .lbl_action =ctk .CTkLabel (trigger_card ,text ="Last Action: None",font =ctk .CTkFont (family ="Segoe UI",size =14 ,weight ="bold"),text_color ="#E67E22")
        self .lbl_action .pack (padx =10 ,pady =25 ,anchor ="center")

        self .pages ["dashboard"]=dash_page 


        settings_page =ctk .CTkFrame (self .main_frame ,fg_color ="transparent")
        settings_page .grid_columnconfigure (0 ,weight =1 )
        settings_page .grid_columnconfigure (1 ,weight =1 )


        thresh_card =ctk .CTkFrame (settings_page ,fg_color ="#181B22",border_width =1 ,border_color ="#2C3E50")
        thresh_card .grid (row =0 ,column =0 ,padx =(0 ,10 ),pady =0 ,sticky ="nsew")

        lbl_thresh_title =ctk .CTkLabel (thresh_card ,text ="Sensitivity Settings",font =ctk .CTkFont (family ="Segoe UI",size =16 ,weight ="bold"),text_color ="#00f0ff")
        lbl_thresh_title .pack (padx =15 ,pady =15 ,anchor ="w")


        self .lbl_slider_x =ctk .CTkLabel (thresh_card ,text =f"Swipe Horizontal Thresh: {self .config ['swipe_threshold_x']:.2f}")
        self .lbl_slider_x .pack (padx =15 ,pady =(5 ,0 ),anchor ="w")
        self .slider_x =ctk .CTkSlider (thresh_card ,from_ =0.05 ,to =0.30 ,command =self .update_slider_x )
        self .slider_x .set (self .config ["swipe_threshold_x"])
        self .slider_x .pack (padx =15 ,pady =5 ,fill ="x")


        self .lbl_slider_y =ctk .CTkLabel (thresh_card ,text =f"Swipe Vertical Thresh: {self .config ['swipe_threshold_y']:.2f}")
        self .lbl_slider_y .pack (padx =15 ,pady =(10 ,0 ),anchor ="w")
        self .slider_y =ctk .CTkSlider (thresh_card ,from_ =0.05 ,to =0.30 ,command =self .update_slider_y )
        self .slider_y .set (self .config ["swipe_threshold_y"])
        self .slider_y .pack (padx =15 ,pady =5 ,fill ="x")


        self .lbl_slider_fist =ctk .CTkLabel (thresh_card ,text =f"Fist Ratio Threshold: {self .config ['fist_ratio_threshold']:.2f}")
        self .lbl_slider_fist .pack (padx =15 ,pady =(10 ,0 ),anchor ="w")
        self .slider_fist =ctk .CTkSlider (thresh_card ,from_ =0.90 ,to =1.60 ,command =self .update_slider_fist )
        self .slider_fist .set (self .config ["fist_ratio_threshold"])
        self .slider_fist .pack (padx =15 ,pady =5 ,fill ="x")


        self .lbl_slider_cd =ctk .CTkLabel (thresh_card ,text =f"Gesture Cooldown (sec): {self .config ['cooldown_seconds']:.1f}")
        self .lbl_slider_cd .pack (padx =15 ,pady =(10 ,0 ),anchor ="w")
        self .slider_cd =ctk .CTkSlider (thresh_card ,from_ =0.5 ,to =3.0 ,command =self .update_slider_cd )
        self .slider_cd .set (self .config ["cooldown_seconds"])
        self .slider_cd .pack (padx =15 ,pady =5 ,fill ="x")


        app_card =ctk .CTkFrame (settings_page ,fg_color ="#181B22",border_width =1 ,border_color ="#2C3E50")
        app_card .grid (row =0 ,column =1 ,padx =(10 ,0 ),pady =0 ,sticky ="nsew")

        lbl_app_title =ctk .CTkLabel (app_card ,text ="App Control Panel",font =ctk .CTkFont (family ="Segoe UI",size =16 ,weight ="bold"),text_color ="#00f0ff")
        lbl_app_title .pack (padx =15 ,pady =15 ,anchor ="w")


        lbl_cam =ctk .CTkLabel (app_card ,text ="Webcam Device Index:")
        lbl_cam .pack (padx =15 ,pady =(5 ,0 ),anchor ="w")
        self .drop_cam =ctk .CTkComboBox (app_card ,values =["0","1","2","3"],command =self .change_camera )
        self .drop_cam .set (str (self .config ["camera_index"]))
        self .drop_cam .pack (padx =15 ,pady =5 ,fill ="x")


        lbl_vsteps =ctk .CTkLabel (app_card ,text ="Volume Steps per Swipe:")
        lbl_vsteps .pack (padx =15 ,pady =(10 ,0 ),anchor ="w")
        self .drop_vsteps =ctk .CTkComboBox (app_card ,values =["2","5","8","10"],command =self .change_vsteps )
        self .drop_vsteps .set (str (self .config ["volume_steps_per_swipe"]))
        self .drop_vsteps .pack (padx =15 ,pady =5 ,fill ="x")


        self .sw_top =ctk .CTkSwitch (app_card ,text ="Float window Always on Top",progress_color ="#00f0ff",command =self .toggle_always_on_top )
        if self .always_on_top_state :
            self .sw_top .select ()
        self .sw_top .pack (padx =15 ,pady =15 ,anchor ="w")


        self .sw_min =ctk .CTkSwitch (app_card ,text ="Minimize to system tray on Close",progress_color ="#00f0ff",command =self .toggle_minimize_on_close )
        if self .minimize_on_close_state :
            self .sw_min .select ()
        self .sw_min .pack (padx =15 ,pady =10 ,anchor ="w")


        self .sw_boot =ctk .CTkSwitch (app_card ,text ="Run automatically on Windows startup",progress_color ="#00f0ff",command =self .toggle_startup )
        if self .config ["startup_registered"]:
            self .sw_boot .select ()
        self .sw_boot .pack (padx =15 ,pady =10 ,anchor ="w")

        self .pages ["settings"]=settings_page 


        help_page =ctk .CTkFrame (self .main_frame ,fg_color ="#181B22",border_width =1 ,border_color ="#2C3E50")

        lbl_help_title =ctk .CTkLabel (help_page ,text ="How to control AirDock",font =ctk .CTkFont (family ="Segoe UI",size =18 ,weight ="bold"),text_color ="#00f0ff")
        lbl_help_title .pack (padx =20 ,pady =20 ,anchor ="w")

        guide_text =(
        "🚀  Alt+Tab App Switcher:\n"
        "   • Swipe Right: Cycles to the Next application (Alt + Tab)\n"
        "   • Swipe Left: Cycles to the Previous application (Alt + Shift + Tab)\n"
        "   • Cycle Control: Keep your hand visible to keep the Alt-Tab window open. Move your hand away to select the app.\n\n"
        "🔊  Windows Volume Control:\n"
        "   • Right Hand Gestures: Controls Volume Up (Swipe / Hold in top section)\n"
        "   • Left Hand Gestures: Controls Volume Down (Swipe / Hold in bottom section)\n"
        "   • Continuous Volume Hold: Hold your Right Hand up to raise volume, or your\n"
        "     Left Hand down to lower volume continuously!\n\n"
        "📸  Instant Screen Capture:\n"
        "   • Fold Palm / Fist: Keep your fingers closed for 0.5 seconds to take\n"
        "     a full screen screenshot!\n\n"
        "💡  Helpful tips:\n"
        "   • Stand 1 to 2 meters away from the camera for natural gesture sweeps.\n"
        "   • When returning your hand to rest, simply drop it downwards towards the middle\n"
        "     of the frame. The built-in cooldown cancels out any return stroke triggers!"
        )

        tb_guide =ctk .CTkTextbox (help_page ,font =ctk .CTkFont (family ="Segoe UI",size =13 ),text_color ="#D1D5DB",fg_color ="transparent",activate_scrollbars =False )
        tb_guide .insert ("0.0",guide_text )
        tb_guide .configure (state ="disabled")
        tb_guide .pack (padx =20 ,pady =(0 ,20 ),fill ="both",expand =True )

        self .pages ["help"]=help_page 

    def show_dashboard (self ):
        self .select_navigation_button (self .btn_dashboard )
        self .hide_all_pages ()
        self .pages ["dashboard"].grid (row =0 ,column =0 ,sticky ="nsew")

    def show_settings (self ):
        self .select_navigation_button (self .btn_settings )
        self .hide_all_pages ()
        self .pages ["settings"].grid (row =0 ,column =0 ,sticky ="nsew")

    def show_help (self ):
        self .select_navigation_button (self .btn_help )
        self .hide_all_pages ()
        self .pages ["help"].grid (row =0 ,column =0 ,sticky ="nsew")

    def select_navigation_button (self ,selected_btn ):
        for btn in [self .btn_dashboard ,self .btn_settings ,self .btn_help ]:
            if btn ==selected_btn :
                btn .configure (fg_color ="#1F2630")
            else :
                btn .configure (fg_color ="transparent")

    def hide_all_pages (self ):
        for page in self .pages .values ():
            page .grid_forget ()


    def update_slider_x (self ,val ):
        self .config ["swipe_threshold_x"]=float (val )
        save_config (self .config )
        self .controller .config =self .config 
        self .lbl_slider_x .configure (text =f"Swipe Horizontal Thresh: {float (val ):.2f}")
        self .lbl_dx .configure (text =f"Move X: 0.00 / {float (val ):.2f}")

    def update_slider_y (self ,val ):
        self .config ["swipe_threshold_y"]=float (val )
        save_config (self .config )
        self .controller .config =self .config 
        self .lbl_slider_y .configure (text =f"Swipe Vertical Thresh: {float (val ):.2f}")
        self .lbl_dy .configure (text =f"Move Y: 0.00 / {float (val ):.2f}")

    def update_slider_fist (self ,val ):
        self .config ["fist_ratio_threshold"]=float (val )
        save_config (self .config )
        self .controller .config =self .config 
        self .lbl_slider_fist .configure (text =f"Fist Ratio Threshold: {float (val ):.2f}")
        self .lbl_fist .configure (text =f"Fist Ratio: 2.00 / {float (val ):.2f}")

    def update_slider_cd (self ,val ):
        self .config ["cooldown_seconds"]=float (val )
        save_config (self .config )
        self .controller .config =self .config 
        self .lbl_slider_cd .configure (text =f"Gesture Cooldown (sec): {float (val ):.1f}")

    def change_camera (self ,val ):
        try :
            cam_idx =int (val )
            self .config ["camera_index"]=cam_idx 
            save_config (self .config )
            self .controller .stop ()
            self .controller .config =self .config 
            self .controller .start ()
        except :
            pass 

    def change_vsteps (self ,val ):
        try :
            steps =int (val )
            self .config ["volume_steps_per_swipe"]=steps 
            save_config (self .config )
            self .controller .config =self .config 
        except :
            pass 

    def toggle_active_state (self ):
        self .enabled_state =self .sidebar_toggle .get ()==1 
        self .config ["enabled"]=self .enabled_state 
        save_config (self .config )
        self .controller .enabled =self .enabled_state 
        if self .enabled_state :
            self .lbl_status .configure (text ="Status: ACTIVE",text_color ="#2ECC71")
        else :
            self .lbl_status .configure (text ="Status: PAUSED",text_color ="#E74C3C")
        if self .tray_icon :
            self .tray_icon .icon =self .create_tray_icon_image ()

    def toggle_always_on_top (self ):
        self .always_on_top_state =self .sw_top .get ()==1 
        self .config ["always_on_top"]=self .always_on_top_state 
        save_config (self .config )
        self .apply_always_on_top ()

    def toggle_minimize_on_close (self ):
        self .minimize_on_close_state =self .sw_min .get ()==1 
        self .config ["minimize_on_close"]=self .minimize_on_close_state 
        save_config (self .config )

    def toggle_startup (self ):
        register_boot =self .sw_boot .get ()==1 
        try :
            key =winreg .OpenKey (winreg .HKEY_CURRENT_USER ,r"Software\Microsoft\Windows\CurrentVersion\Run",0 ,winreg .KEY_SET_VALUE )
            if register_boot :
                script_path =os .path .abspath (__file__ )

                if getattr (sys ,'frozen',False ):
                    command =f'"{sys .executable }"'
                else :
                    pythonw_path =os .path .join (os .path .dirname (sys .executable ),"pythonw.exe")
                    if not os .path .exists (pythonw_path ):
                        pythonw_path =sys .executable .replace ("python.exe","pythonw.exe")
                    command =f'"{pythonw_path }" "{script_path }"'
                winreg .SetValueEx (key ,"GestureController",0 ,winreg .REG_SZ ,command )
                self .config ["startup_registered"]=True 
                print ("Registered startup.")
            else :
                try :
                    winreg .DeleteValue (key ,"GestureController")
                except :
                    pass 
                self .config ["startup_registered"]=False 
                print ("Deregistered startup.")
            winreg .CloseKey (key )
        except Exception as e :
            print (f"Failed to modify startup registry: {e }")
        save_config (self .config )

    def apply_always_on_top (self ):
        self .attributes ("-topmost",self .always_on_top_state )

    def on_frame_processed (self ,frame ,gesture ,status ):
        """Called by capture thread when frame analysis completes."""
        self ._put_latest (self .queue ,(frame ,gesture ,status ))

    def _put_latest (self ,q ,item ):
        try :
            q .get_nowait ()
        except queue .Empty :
            pass 
        try :
            q .put_nowait (item )
        except queue .Full :
            pass 

    def poll_queue (self ):
        """Fetches the latest frame from queue and updates the CustomTkinter display canvas."""
        try :
            frame ,gesture ,status =self .queue .get_nowait ()


            self .lbl_fps .configure (text =f"FPS: {self .controller .fps }")

            thresh_x =self .config ["swipe_threshold_x"]
            thresh_y =self .config ["swipe_threshold_y"]
            thresh_fist =self .config ["fist_ratio_threshold"]

            self .lbl_dx .configure (text =f"Move X: {self .controller .current_dx :+.2f} / {thresh_x :.2f}")
            self .lbl_dy .configure (text =f"Move Y: {self .controller .current_dy :+.2f} / {thresh_y :.2f}")
            self .lbl_fist .configure (text =f"Fist Ratio: {self .controller .current_fist_ratio :.2f} / {thresh_fist :.2f}")


            px =np .clip ((self .controller .current_dx +0.3 )/0.6 ,0.0 ,1.0 )
            py =np .clip ((self .controller .current_dy +0.3 )/0.6 ,0.0 ,1.0 )
            pf =np .clip (self .controller .current_fist_ratio /2.0 ,0.0 ,1.0 )

            self .bar_dx .set (px )
            self .bar_dy .set (py )
            self .bar_fist .set (pf )

            if self .controller .last_triggered_action :
                self .lbl_action .configure (text =f"Last Action: {self .controller .last_triggered_action }")



            frame_resized =cv2 .resize (frame ,(380 ,285 ))
            frame_rgb =cv2 .cvtColor (frame_resized ,cv2 .COLOR_BGR2RGB )
            pil_img =Image .fromarray (frame_rgb )
            ctk_img =ctk .CTkImage (light_image =pil_img ,dark_image =pil_img ,size =(380 ,285 ))

            self .canvas .configure (image =ctk_img )
            self .canvas .image =ctk_img 

        except queue .Empty :
            pass 

        self .after (15 ,self .poll_queue )

    def on_window_close (self ):
        """Intercepts window close button to minimize or close."""
        if self .minimize_on_close_state :
            self .withdraw ()
            print ("App minimized to system tray.")
        else :
            self .on_quit_app ()

    def create_tray_icon_image (self ):
        """Generate a simple tray icon image."""
        from PIL import Image ,ImageDraw 
        image =Image .new ('RGB',(64 ,64 ),color =(30 ,30 ,30 ))
        draw =ImageDraw .Draw (image )
        draw .rectangle ([16 ,16 ,48 ,48 ],fill =(0 ,255 ,255 ))
        return image 

    def setup_system_tray (self ):
        """Creates a background system tray thread."""
        def restore_window (icon ,item ):
            self .deiconify ()
            self .lift ()
            self .apply_always_on_top ()

        def toggle_enable_tray (icon ,item ):
            self .sidebar_toggle .toggle ()
            self .toggle_active_state ()

        def quit_tray (icon ,item ):
            self .on_quit_app ()

        menu =pystray .Menu (
        pystray .MenuItem ("Show Control Center",restore_window ,default =True ),
        pystray .MenuItem (lambda text :"Disable Gestures"if self .enabled_state else "Enable Gestures",toggle_enable_tray ),
        pystray .Menu .SEPARATOR ,
        pystray .MenuItem ("Quit App",quit_tray )
        )

        self .tray_icon =pystray .Icon (
        "airdock",
        self .create_tray_icon_image (),
        "Gesture Control Center",
        menu 
        )


        tray_thread =threading .Thread (target =self .tray_icon .run ,daemon =True )
        tray_thread .start ()

    def on_quit_app (self ):
        print ("Shutdown requested...")
        self .controller .stop ()
        if self .tray_icon :
            self .tray_icon .stop ()
        self .destroy ()
        sys .exit (0 )


if __name__ =="__main__":
    app =PremiumApp ()
    app .mainloop ()
