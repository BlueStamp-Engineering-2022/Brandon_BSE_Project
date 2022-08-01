Python 3.10.5 (v3.10.5:f377153967, Jun  6 2022, 12:36:10) [Clang 13.0.0 (clang-1300.0.29.30)] on darwin
Type "help", "copyright", "credits" or "license()" for more information.
import time
import picamera

import boto3
import serial

s3 = boto3.resource('s3')

import RPi.GPIO as GPIO

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

import pygame

path = "/home/frootytoots16/Desktop/ynsounds/"
pygame.mixer.init()
speaker_volume = 1
pygame.mixer.music.set_volume(speaker_volume)


ser=serial.Serial('/dev/ttyACM0', 9600, timeout=1)
ser.write(b"close\n")

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(4, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(24, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
previn = 1
count = 0
BUCKET = "frooty-bucket"
KEY = "guest2.jpeg"
IMAGE_ID = KEY
COLLECTION = "guest_collection"
dynamodb = boto3.client('dynamodb',"us-west-1")

def gpio_callback():
	capture_image()
	time.sleep(0.3)
	upload_image()
	time.sleep(2)
	guest_search('frooty-bucket', 'guest2.jpeg', 'guest-collection')
	return

def but(Pin4):
    global previn
    global count
    inp=GPIO.input(Pin4)
    if (inp and (Pin4 == 24)):
        print("Overwriting")
        ser.reset_input_buffer()
        ser.write(b"open\n")
        print ("The door is open")
        time.sleep(10)
        ser.write(b"close\n")
        print ("The door is locked")
        print ("\n")
    elif ((not previn) and inp):
        count = count + 1
        gpio_callback()
    previn = inp
    time.sleep(0.05)

#GPIO.add_event_detect(4, GPIO.FALLING, callback=gpio_callback, bouncetime=3000)


def capture_image():
	with picamera.PiCamera() as camera:
		camera.resolution = (640, 480)
		camera.start_preview()
		camera.capture('guest2.jpeg')
		camera.stop_preview()
		camera.close()
		return
		
				
def upload_image(FullName='Guest'):
	file = open('guest2.jpeg','rb')
	object = s3.Object('frooty-bucket','guest2.jpeg')
	ret = object.put(Body=file,
			Metadata={'FullName':FullName}
			)
	#print(ret)
	return


def send_email(): 
    fromaddr = "dontclickme@gmail.com"
    toaddr = "donttrythisemail@gmail.com"
     
    msg = MIMEMultipart()
     
    msg['From'] = fromaddr
    msg['To'] = toaddr
    msg['Subject'] = "New Guest"
     
    body = "There's someone at the door. Here's a photo of them: "
     
    msg.attach(MIMEText(body, 'plain'))
     
    filename = "guest2.jpeg"
    attachment = open("/home/frootytoots16/guest2.jpeg", "rb")
     
    part = MIMEBase('application', 'octet-stream')
    part.set_payload((attachment).read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', "attachment; filename= %s" % filename)
     
    msg.attach(part)
     
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(fromaddr, "password")
    text = msg.as_string()
    server.sendmail(fromaddr, toaddr, text)

def guest_search(bucket, key, collection_id, image_id=None, attributes=(), region="us-west-1"):
    rekognition = boto3.client("rekognition", region)
    card_title = "Guest's Identity"
    session_attributes = {}
    should_end_session = True
    speech_output = "I dont know the person."
    reprompt_text = ""
    try:
        response = rekognition.search_faces_by_image(CollectionId='guest_collection', Image={"S3Object": {"Bucket": BUCKET,"Name": KEY,}},)
        if len(response['FaceMatches']) == 0:
            pygame.mixer.music.load(path + "leave.wav")
            pygame.mixer.music.play()
            GPIO.setup(18, GPIO.OUT)
            GPIO.output(18, True)
            time.sleep(2)
            GPIO.output(18, False)
            print ("No face was matched. An image of the guest was sent to your email.")
            print ("\n")
            send_email()
        else:
    	    for match in response['FaceMatches']:
                face = dynamodb.get_item(
				TableName='guest_collection',  
				Key={'RekognitionId': {'S': match['Face']['FaceId']}}
				)
                #print(face)
                if 'Item' in face:
                        guest = face['Item']['FullName']['S']
                        speech_output = guest + " is outside the door."
	        		#print (face['Item']['FullName']['S'])
            		#guest = face['Item']['FullName']['S']
            		#speech_output = " is waiting at the door." 
                        reprompt_text = ""
                        print (speech_output)
                        ser.reset_input_buffer()
                        ser.write(b"open\n")
                        print ("The door is open")
                        pygame.mixer.music.load(path + "enter.wav")
                        pygame.mixer.music.play()
                        GPIO.setup(23, GPIO.OUT)
                        GPIO.output(23, True)
                        time.sleep(2)
                        GPIO.output(23, False)
                        time.sleep(10)
                        ser.write(b"close\n")
                        print ("The door is locked")
                        print ("\n")
                        break

    except:
        GPIO.setup(18, GPIO.OUT)
        GPIO.output(18, True)
        time.sleep(2)
        GPIO.output(18, False)

        pygame.mixer.music.load(path + "leave.wav")
        pygame.mixer.music.play()

        print ("There was no face found.")
        print("\n")

try:
    while True:
        but(4)
        but(24)

except KeyboardInterrupt:
    GPIO.cleanup()