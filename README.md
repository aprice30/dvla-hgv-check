# DVLA HGV Check

Since living near a small road with a 7.5t weight limit we have noticed a large number of lorries 
breaking this and using it as a shortcut. 

The solution is to report them to the concil who then prosecute the driver and firm. Sadly you have to be around to photo the lorry and capture the number plate for it to be of use.

This project aims to setup a Computer Vision solution to monitor a road. When motion is detected it will aim to get a number plate from the image. If possible it will use this to query the DVLA to determine if it is > 7.5t. From this it can then be reported to the council.s