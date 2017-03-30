#!/usr/bin/env python
# created by chris@drumminhands.com
# see instructions at http://www.drumminhands.com/2014/06/15/raspberry-pi-photo-booth/


import os
import glob
import random
import time
import traceback
import re
from time import sleep
import RPi.GPIO as GPIO #using physical pin numbering change in future?
import picamera # http://picamera.readthedocs.org/en/release-1.4/install2.html
import atexit
import sys, getopt
import socket
import pygame
import cups
import fcntl
import struct
import commands
import uuid
from PIL import Image, ImageDraw, ImageFont
import pytumblr # https://github.com/tumblr/pytumblr
#from twython import Twython
import config
import shutil
import datetime as dt
from signal import alarm, signal, SIGALRM, SIGKILL
from PIL import Image, ImageDraw

########################
### Variables Config ###
########################
generated_tag = ""
generated_filepath = ""

led1_pin = 15 # LED 1
led2_pin = 19 # LED 2
led3_pin = 21 # LED 3
led4_pin = 23 # LED 4

MakeWatermark = 1 # 1 = Watermark on pics,
MakeAnimatedGif = 0 # 1 = animated gif, 
MakeMosaic = 0 # 1 = animated gif,

button1_pin = 22 # pin for the big red button
button2_pin = 18 # pin for button to shutdown the pi
button3_pin = 16 # pin for button to end the program, but not shutdown the pi

enable_color_effects = 0 # default 1. Change to 0 if you don't want to upload pics.
enable_image_effects = 0 # default 1. Change to 0 if you don't want to upload pics.
post_online = 0 # default 1. Change to 0 if you don't want to upload pics.

total_pics = 4 # number of pics to be taken
capture_delay = 0.5 # delay between pics
prep_delay = 3 # number of seconds at step 1 as users prep to have photo taken
gif_delay = 100 # How much time between frames in the animated gif
restart_delay = 4 # how long to display finished message before beginning a new session

#Taille du moniteur
monitor_w = 1280 #
monitor_h = 1024 #
#resolution de la camera PI
camera_pi_w = 1280 #
camera_pi_h = 1024 #
#resolution des photo de l appreil photo:
photo_w = 3008 #
photo_h = 2000 #


transform_x = monitor_w #1280 # how wide to scale the jpg when replaying
transform_y = monitor_h #1024 #how high to scale the jpg when replaying
offset_x = 0 # how far off to left corner to display photos
offset_y = 0 # how far off to left corner to display photos

replay_delay = 3 # how much to wait in-between showing pics on-screen after taking
replay_cycles = 1 # how many times to show each photo on-screen after taking

test_server = 'www.google.com'
real_path = os.path.dirname(os.path.realpath(__file__))

folder_images = real_path + '/images/' # path to save images

file_path = '/home/pi/drive_ext' # path to save images
folder_pics = '/pics/' # path to save images
folder_pics_w = '/pics_w/' # path to save images with watermark
folder_screen = '/screen/' # path to save images with watermark
folder_tumblr = '/tumblr/' # path to save images with watermark
folder_gif = '/gif/' # path to save gif
folder_mosaic = '/mosaic/' # path to save gif

font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSans.ttf", 700)

#extract the ip address (or addresses) from ifconfig
found_ips = []
ips = re.findall( r'[0-9]+(?:\.[0-9]+){3}', commands.getoutput("/sbin/ifconfig"))
for ip in ips:
  if ip.startswith("255") or ip.startswith("127") or ip.endswith("255"):
    continue
  found_ips.append(ip)

# Setup the tumblr OAuth Client
client = pytumblr.TumblrRestClient(
    config.consumer_key,
    config.consumer_secret,
    config.oath_token,
    config.oath_secret,
);

####################
### Other Config ###
####################
GPIO.setmode(GPIO.BOARD)

GPIO.setup(led1_pin,GPIO.OUT) # LED 1
GPIO.setup(led2_pin,GPIO.OUT) # LED 2
GPIO.setup(led3_pin,GPIO.OUT) # LED 3
GPIO.setup(led4_pin,GPIO.OUT) # LED 4

GPIO.setup(button1_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP) # falling edge detection on button 1
GPIO.setup(button2_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP) # falling edge detection on button 2
GPIO.setup(button3_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP) # falling edge detection on button 3

GPIO.output(led1_pin,False);
GPIO.output(led2_pin,False);
GPIO.output(led3_pin,False);
GPIO.output(led4_pin,False); 

#################
### Functions ###
#################
   
def cleanup():
  print('Ended abruptly')
  GPIO.cleanup()
atexit.register(cleanup)

def shut_it_down(channel):  
    print ("Shutting down...") 
    GPIO.output(led1_pin,False);
    GPIO.output(led2_pin,False);
    GPIO.output(led3_pin,False);
    GPIO.output(led4_pin,False);
    time.sleep(1)
    os.system("sudo halt")

def exit_photobooth(channel):
    print ("Photo booth app ended. RPi still running") 
    GPIO.output(led1_pin,False);
    GPIO.output(led2_pin,False);
    GPIO.output(led3_pin,False);
    GPIO.output(led4_pin,False);
    time.sleep(1)
    sys.exit()
	
def countdown(camera):
	overlay_renderer = None
	for j in range(1,4):
		img = Image.new("RGB", (monitor_w, monitor_h))
		draw = ImageDraw.Draw(img)
		draw.text(((monitor_w/2)-200,(monitor_h/2)-400), str(4-j), (255, 255, 255), font=font)
		if not overlay_renderer:
#		if j=1:
			overlay_renderer = camera.add_overlay(img.tostring(),layer=3,size=img.size,alpha=128);
		else:
			overlay_renderer.update(img.tostring())
		sleep(1)

	img = Image.new("RGB", (monitor_w, monitor_h))
	draw = ImageDraw.Draw(img)
	draw.text((monitor_w/2,monitor_h/2), " ", (255, 255, 255), font=font)
	overlay_renderer.update(img.tostring())
	camera.remove_overlay(overlay_renderer)
	
def is_connected():
	try:
		print "Connection test"
		# see if we can resolve the host name -- tells us if there is
		# a DNS listening
		print socket.gethostbyname(test_server)
		host = socket.gethostbyname(test_server)
		print "Connection test 2"
		# connect to the host -- tells us if the host is actually
		# reachable
		s = socket.create_connection((host, 80), 2)
		print "Connection OK"
		return True
	except:
		pass
	return False  

def tag_gen(size=5):
		random = str(uuid.uuid4()) # Convert UUID format to a Python string.
		random = random.upper() # Make all characters uppercase.
		random = random.replace("-","") # Remove the UUID '-'.
		return random[0:size] # Return the random string. 

def init_pygame():
    pygame.init()
    size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
    pygame.display.set_caption('Photo Booth Pics')
    pygame.mouse.set_visible(False) #hide the mouse cursor	
    return pygame.display.set_mode(size, pygame.FULLSCREEN)

def set_dimensions(img_w, img_h):
    # set variables to properly display the image on screen

    # connect to global vars
    global transform_y, transform_x, offset_y, offset_x

    # based on output screen resolution, calculate how to display
    ratio_h = (monitor_w * img_h) / img_w 

    if (ratio_h < monitor_h):
        #Use horizontal black bars
        transform_y = ratio_h
        transform_x = monitor_w
        offset_y = (monitor_h - ratio_h) / 2
        offset_x = 0
    elif (ratio_h > monitor_h):
        #Use vertical black bars
        transform_x = (monitor_h * img_w) / img_h
        transform_y = monitor_h
        offset_x = (monitor_w - transform_x) / 2
        offset_y = 0
    else:
        #No need for black bars as photo ratio equals screen ratio
        transform_x = monitor_w
        transform_y = monitor_h
        offset_y = offset_x = 0

    # uncomment these lines to troubleshoot screen ratios
    #print str(img_w) + " x " + str(img_h)
    #print "ratio_h: "+ str(ratio_h)
    #print "transform_x: "+ str(transform_x)
    #print "transform_y: "+ str(transform_y)
    #print "offset_y: "+ str(offset_y)
    #print "offset_x: "+ str(offset_x)
	
def show_image(image_path, t):

	#global transform_y, transform_x, offset_y, offset_x

	screen = init_pygame()
	img=pygame.image.load(image_path).convert()
	set_dimensions(img.get_width(), img.get_height())
	img = pygame.transform.scale(img,(transform_x,transform_y))
	
#	sprite = pygame.sprite.Sprite()
#	sprite.image = img
#	sprite.rect = img.get_rect()
	
#	font = pygame.font.SysFont('Sans', 20)
#	text=font.render(t, 1,(255,255,255))
#	sprite.image.blit(text, (10, 10))
	
#	group = pygame.sprite.Group()
#	group.add(sprite)
#	group.draw(screen)
	
	screen.blit(img,(offset_x,offset_y))
	pygame.display.flip()
	
	
def display_pics(jpg_group):
    # this section is an unbelievable nasty hack - for some reason Pygame
    # needs a keyboardinterrupt to initialise in some limited circs (second time running)
#    class Alarm(Exception):
#        pass
#    def alarm_handler(signum, frame):
#        raise Alarm
#    signal(SIGALRM, alarm_handler)
#    alarm(3)
#    try:
#        #screen = init_pygame()
#        alarm(0)
#    except Alarm:
#        raise KeyboardInterrupt
	for i in range(0, total_pics): #show each pic
		if MakeWatermark:
			print "Creating an Watermark" 
			try:
				create_watermark(jpg_group,i)
				filename = generated_filepath_pics_w + jpg_group + "-0" + str(i) + ".jpg"
			except Exception, e:
				tb = sys.exc_info()[2]
				traceback.print_exception(e.__class__, e, tb)
		else:
			filename = generated_filepath_pics + jpg_group + "-0" + str(i) + ".jpg"
		
		print filename
		show_image(filename, "");

		filename3 = "cp " + generated_filepath_pics_w + jpg_group + "-0" + str(i) + ".jpg " + generated_filepath_tumblr + jpg_group + "-0" + str(i) + ".jpg"
		print filename3
		os.system(filename3)
		
		time.sleep(replay_delay) # pause 

def create_watermark(jpg_group,i): 
#	for i in range(0, total_pics): #Add watermark on each pic
		graphicsmagick = "convert " + generated_filepath_pics + jpg_group + "-0" + str(i) + ".jpg " + folder_images + "watermark.png -gravity southeast -compose over -composite " + generated_filepath_pics_w + jpg_group + "-0" + str(i) + ".jpg"
		print "Resizing with command: " + graphicsmagick
		os.system(graphicsmagick) 

def create_mosaic(jpg_group): 
	print "Montaging Pics..."
#	graphicsmagick = "gm mogrify -resize 968x648 " + generated_filepath_pics + now + "*_small.jpg" 
#	print "Resizing with command: " + graphicsmagick
#	os.system(graphicsmagick) 
	graphicsmagick = "gm montage " + generated_filepath_pics + jpg_group + "*.jpg -geometry 3000x2000+30+30 -tile 2x2 " + generated_filepath_mosaic + jpg_group + "_mosaic.jpg" 
	print "Montaging images with command: " + graphicsmagick
	os.system(graphicsmagick) 
	
# define the photo taking function for when the big button is pressed 
def start_photobooth(): 
	################################# Begin Step 1 ################################# 
        GPIO.output(led4_pin,False);
	show_image(folder_images + "blank.png", "")
	print "Get Ready"
	#GPIO.output(led1_pin,True);
	show_image(folder_images + "instructions.png", "")
	sleep(prep_delay) 

	#GPIO.output(led1_pin,False)
	show_image(folder_images + "blank.png", "")
	
	camera = picamera.PiCamera()
	pixel_width = monitor_w#1000 #use a smaller size to process faster, and tumblr will only take up to 500 pixels wide for animated gifs
	pixel_height = monitor_h * pixel_width // monitor_w
	#camera.resolution = (pixel_width, pixel_height)
	camera.resolution = (camera_pi_w, camera_pi_h) 
	camera.vflip = False#True
	camera.hflip = False
	
	#camera.sharpness = 10
	#camera.contrast = 30
	#camera.brightness = 60
	#camera.saturation = 50
	
	camera.video_stabilization = True
	camera.exposure_compensation = 0
	camera.exposure_mode = 'night'
	#camera.meter_mode = 'average'
	#camera.awb_mode = 'auto'
	
	#random effect (filter and color)
	if enable_color_effects:
		colour = (random.randint(0, 256),random.randint(0, 256))
		print "Colour effect: " + str(colour)
		camera.color_effects = colour
	
	if enable_image_effects:
		image_effect = picamera.PiCamera.IMAGE_EFFECTS.keys()[random.randint(0, len(picamera.PiCamera.IMAGE_EFFECTS))]	
		print "Filter effect: " + image_effect
		camera.image_effect = image_effect
	
	#camera.saturation = -20 # comment out this line if you want color images
	#camera.start_preview()
	#sleep(2) #warm up camera
	
	################################# Begin Step 2 #################################
	print "Begin Step 2"
	GPIO.output(led1_pin,True) #turn on the LED
	now = time.strftime("%Y-%m-%d-%H-%M-%S") #get the current date and time for the start of the filename
	try: #take the photos
		#for i, filename in enumerate(camera.capture_continuous(config.file_path + now + '-' + '{counter:02d}.jpg')):
		for i in range(0, total_pics):
			camera.start_preview()
			#sleep(1) #warm up camera
			filename = generated_filepath_pics + now + "-0" + str(i) + ".jpg"
			countdown(camera)
			print "Taking pics" + str(i)
			camera.stop_preview()#ju
			sleep(0.25)
			show_image(folder_images + "capture.png", "")
#			GPIO.output(led1_pin,True) #turn on the LED
			take_pic_command = "gphoto2 --capture-image-and-download --filename " + filename +" --force-overwrite"
			print take_pic_command
			os.system(take_pic_command) 
			#camera.capture(filename)
			print(filename)

#			sleep(0.25) #pause the LED on for just a bit
#			GPIO.output(led1_pin,False) #turn off the LED
#			sleep(capture_delay) # pause in-between shots
			if i == total_pics-1:
				break
	finally:
		camera.stop_preview()
		camera.close()
		GPIO.output(led1_pin,False) #turn on the LED
		
	########################### Begin Step 3 #################################
	print "Begin Step 3"
	show_image(folder_images + "processing.png", "")
	try:
		display_pics(now)
	except Exception, e:
		tb = sys.exc_info()[2]
		traceback.print_exception(e.__class__, e, tb)
		
	########################### Begin Step 4 #################################
	print "Begin Step 4"
    	if post_online:
		show_image(folder_images + "finished.png", "")
	else:
		show_image(folder_images + "processing.png", "")
	if MakeAnimatedGif:
		print "Creating an animated gif" 
		GPIO.output(led3_pin,True) #turn on the LED
		graphicsmagick = "gm convert -delay " + str(gif_delay) + " " + generated_filepath_pics_w + now + "*.jpg " + generated_filepath_gif + now + ".gif" 
		os.system(graphicsmagick) #make the .gif
	
	if MakeMosaic:
		print "Creating an Mosaic" 
		try:
			create_mosaic(now)
		except Exception, e:
			tb = sys.exc_info()[2]
			traceback.print_exception(e.__class__, e, tb)
	if MakeMosaic:
              filename = generated_filepath_mosaic + now + "_mosaic.jpg"
              print filename
              show_image(filename, "");
              time.sleep(4) # pause 
			
	########################### Begin Step 5 #################################
	print "Begin Step 5"
	if post_online: # turn off posting pics online in the variable declarations at the top of this document
		show_image(folder_images + "uploading.png", "")
		print "Uploading to tumblr. Please check " + config.tumblr_blog + ".tumblr.com soon."
		connected = is_connected() #check to see if you have an internet connection
		while connected: 
			print "connected"
			try:
				if MakeAnimatedGif:
                                        print "Uploading Gif"
					file_to_upload = generated_filepath_gif + now + ".gif"
					print file_to_upload
					client.create_photo(config.tumblr_blog, state="published", tags=["Melle", "40th", "Birthday", now], data=file_to_upload)

				if MakeMosaic:
					print "Uploading Mosaic"
					file_to_upload = generated_filepath_mosaic + now + "_mosaic.jpg"
					client.create_photo(config.tumblr_blog, state="published", tags=["Melle", "40th", "Birthday", now], data=file_to_upload)
				break
			except ValueError:
				print "Oops. No internect connection. Upload later."
				try: #make a text file as a note to upload the .gif later
					print "Merde"
					file = open(generated_filepath_pics + now + "-FILENOTUPLOADED.txt",'w')   # Trying to create a new file or open one
					file.close()
				except:
					print('Something went wrong. Could not write file.')
					#sys.exit(0) # quit Python
					
	GPIO.output(led3_pin,False) #turn off the LED
	sleep(1) #pause the LED on for just a bit
	########################### Begin Step 6 #################################
	print "Begin Step 6"
	GPIO.output(led4_pin,True) #turn on the LED
	#pygame.quit()
	print "Done"
	GPIO.output(led4_pin,False) #turn off the LED
	
	if post_online:
		show_image(folder_images + "finished.png", "")
	else:
		show_image(folder_images + "finished2.png", "")
	
	time.sleep(restart_delay)
	GPIO.output(led4_pin,True);
	show_image(folder_images + "intro.png", "");
	
	GPIO.remove_event_detect(button2_pin)
	GPIO.add_event_detect(button2_pin, GPIO.FALLING, callback=shut_it_down, bouncetime=1000) 
	
####################
### Main Program ###
####################

# when a falling edge is detected on button2_pin and button3_pin, regardless of whatever   
# else is happening in the program, their function will be run   
#GPIO.add_event_detect(button2_pin, GPIO.FALLING, callback=shut_it_down, bouncetime=300)
#generated_tag = "/" + tag_gen(6) + "/"
generated_tag = ""

generated_filepath_pics = file_path + folder_pics + generated_tag 
if not os.path.exists(generated_filepath_pics):
    os.makedirs(generated_filepath_pics)

generated_filepath_pics_w = file_path + folder_pics_w + generated_tag
if not os.path.exists(generated_filepath_pics_w):
    os.makedirs(generated_filepath_pics_w)

generated_filepath_gif = file_path + folder_gif + generated_tag
if not os.path.exists(generated_filepath_gif):
    os.makedirs(generated_filepath_gif)
	
generated_filepath_mosaic = file_path + folder_mosaic + generated_tag
if not os.path.exists(generated_filepath_mosaic):
    os.makedirs(generated_filepath_mosaic)
	
generated_filepath_screen = file_path + folder_screen + generated_tag
if not os.path.exists(generated_filepath_screen):
    os.makedirs(generated_filepath_screen)
	
generated_filepath_tumblr = file_path + folder_tumblr + generated_tag
if not os.path.exists(generated_filepath_tumblr):
    os.makedirs(generated_filepath_tumblr)
	
print "PartyPics app running..." 
GPIO.output(led1_pin,True); #light up the lights to show the app is running
GPIO.output(led2_pin,True);
##GPIO.output(led3_pin,True);
GPIO.output(led4_pin,True);

time.sleep(0.3)

GPIO.output(led1_pin,False); #turn off the lights
#GPIO.output(led2_pin,False);
#GPIO.output(led3_pin,False);
#GPIO.output(led4_pin,False);

#print "IP: "+"\r\n".join(found_ips)
show_image(folder_images + "intro.png", "IP: "+"\r\n".join(found_ips));
#show_image(folder_images + "intro.png", "");
#time.sleep(1)

GPIO.add_event_detect(button2_pin, GPIO.FALLING, callback=shut_it_down, bouncetime=1000) 
GPIO.add_event_detect(button3_pin, GPIO.FALLING, callback=exit_photobooth, bouncetime=1000) 

try:  
	while True:
		GPIO.wait_for_edge(button1_pin, GPIO.BOTH)
		time.sleep(0.5) #debounce
		start_photobooth()
except KeyboardInterrupt:  
    # here you put any code you want to run before the program   
    # exits when you press CTRL+C  
    print "\n", counter # print value of counter  
  
except:  
    # this catches ALL other exceptions including errors.  
    # You won't get any error messages for debugging  
    # so only use it once your code is working  
    print "Other error or exception occurred!"  
  
finally:  
    GPIO.cleanup() # this ensures a clean exit  
