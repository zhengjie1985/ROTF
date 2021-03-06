from statistics import mode
import socket
import time
import cv2
from keras.models import load_model
import numpy as np
import urllib
import imutils

from utils.datasets import get_labels
from utils.inference import detect_faces
from utils.inference import draw_text
from utils.inference import draw_bounding_box
from utils.inference import apply_offsets
from utils.inference import load_detection_model
from utils.preprocessor import preprocess_input

# parameters for loading data and images
detection_model_path = '/home/shreeyash/opencv/data/haarcascades/haarcascade_frontalface_default.xml'
emotion_model_path = '/home/shreeyash/Desktop/Deep Learning/emotion/fer2013_mini_XCEPTION.102-0.66.hdf5'
emotion_labels = get_labels('fer2013')

# hyper-parameters for bounding boxes shape
frame_window = 10
emotion_offsets = (20, 40)

# loading models
face_detection = load_detection_model(detection_model_path)
emotion_classifier = load_model(emotion_model_path, compile=False)

# getting input model shapes for inference
emotion_target_size = emotion_classifier.input_shape[1:3]

# starting lists for calculating modes
emotion_window = []

# starting video streaming
cv2.namedWindow('window_frame')
url = "http://10.42.0.23:8080/shot.jpg"  # Write IP of your mobile.
count = 0
while True:
    img = urllib.request.urlopen(url)
    img = np.array(bytearray(img.read()),dtype=np.uint8)
    bgr_image = cv2.imdecode(img, -1)
    try:
        gray_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY)
        rgb_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
        faces = detect_faces(face_detection, gray_image)

        for face_coordinates in faces:

            x1, x2, y1, y2 = apply_offsets(face_coordinates, emotion_offsets)
            gray_face = gray_image[y1:y2, x1:x2]
            Y = (y2+y1)//2
            X = (x2+x1)//2
            #cv2.imshow('gray_face', gray_face)
            try:
                gray_face = cv2.resize(gray_face, (emotion_target_size))
            except:
                continue

            gray_face = preprocess_input(gray_face, True)
            gray_face = np.expand_dims(gray_face, 0)
            gray_face = np.expand_dims(gray_face, -1)
            emotion_prediction = emotion_classifier.predict(gray_face)
            emotion_probability = np.max(emotion_prediction)
            emotion_label_arg = np.argmax(emotion_prediction)
            emotion_text = emotion_labels[emotion_label_arg]
            emotion_window.append(emotion_text)

            if len(emotion_window) > frame_window:
                emotion_window.pop(0)
            try:
                emotion_mode = mode(emotion_window)
            except:
                continue

            if emotion_text == 'angry':
                color = emotion_probability * np.asarray((255, 0, 0))
            elif emotion_text == 'sad':
                color = emotion_probability * np.asarray((0, 0, 255))
            elif emotion_text == 'happy':
                color = emotion_probability * np.asarray((255, 255, 0))
            elif emotion_text == 'surprise':
                color = emotion_probability * np.asarray((0, 255, 255))
            else:
                color = emotion_probability * np.asarray((0, 255, 0))
            #======= To be transferred to raspberry pi
            # transferred string is like : "X,Y,emotion"
            data = str(X) + "," + str(Y) + "," + str(emotion_text)
            print(data)
            print("count", count)
            count = count + 1
            if count >= 20:
                count = 0
                try:
                    s = socket.socket()
                    s.connect(('10.42.0.24', 3125))
                    s.sendall(data.encode())
                    s.close()
                    print(data)
                except:
                    print("No connection!!")
            #==========================================
            color = color.astype(int)
            color = color.tolist()

            draw_bounding_box(face_coordinates, rgb_image, color)
            draw_text(face_coordinates, rgb_image, emotion_mode,
                      color, 0, -45, 1, 1)

        bgr_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)
        cv2.imshow('window_frame', bgr_image)
        sleep(1)
    except:
        print("No device or image found!")
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
