The NVS component
=================

Integration of video streaming over UPD in H264.
Component name: `NVS`.

Configuration
-------------
For proper configuration of the streaming using HA, be careful.
An API issue is happening preventing proper advertising of H264 DPB level with GST/V4L2.
Refer to `this link <https://en.wikipedia.org/wiki/Advanced_Video_Coding#Decoded_picture_buffering>` for more information on how to set the level of encoded output.
Not specifying it will make the encoding fail.
