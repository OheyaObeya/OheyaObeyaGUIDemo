# OheyaObeyaGUIDemo
OheyaObeyaGUIDemo is a tool to introduce OheyaObeya models briefly.   
It classifies the desk situation (clean / so-so / messy) in real time from the image taken by the USB camera.

**Note:**   
- Internally, [OheyaObeyaWebAPI](https://github.com/OheyaObeya/OheyaObeyaWebAPI) is called.

## Demo Movie
[![Demo Movie](http://img.youtube.com/vi/Pub1_Nes1tM/0.jpg)](http://www.youtube.com/watch?v=Pub1_Nes1tM)

This video is a demo to predict a desk situation (clean / so-so / messy). The prediction result (clean / so-so / messy) is displayed on the top left of the screen.

This classification model was created using Keras.  

**DEMO 1:** Clean / Messy Classification   
Depending on the placement of the objects, the prediction result changes.

**DEMO 2:** Obeya Alarm (Obeya = very messy room)   
If the desk is left messy, the alarm will sound, and the message will be posted to Slack.
To stop the alarm, you have to clear the desk.
