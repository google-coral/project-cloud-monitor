# Inference at the Edge
In this part, you will set up Coral Dev Board and IoT Core.

## Prerequisites
First of all you must set up Coral Dev Board if you did not yet, follow [this official instruction](https://coral.withgoogle.com/docs/dev-board/get-started/). 
Also make sure if you can [run a model with camera](https://coral.withgoogle.com/docs/dev-board/camera/).

## Set up Coral Dev Board

1. Install required libraries
```
echo "deb https://packages.cloud.google.com/apt coral-cloud-stable main" | sudo tee /etc/apt/sources.list.d/coral-cloud.list

curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -

sudo apt update

sudo apt install python3-coral-cloudiot
```

2. Clone this repository
```
$ git clone https://github.com/google-coral/project-cloud-monitor
```

3. Download pretrained model
```
$ export DEMO_FILES="$HOME/demo_files"
$ wget -P ${DEMO_FILES}/ https://dl.google.com/coral/canned_models/mobilenet_ssd_v1_coco_quant_postprocess_edgetpu.tflite
$ wget -P ${DEMO_FILES}/ https://dl.google.com/coral/canned_models/coco_labels.txt
```

## Cloud IoT Core
Each device must be registered to IoT Core in order to publish data and receive config.

1. [Enable IoT Core and Pub/Sub](https://console.cloud.google.com/flows/enableapi?apiid=cloudiot.googleapis.com,pubsub)
2. [Create a device registry](https://cloud.google.com/iot/docs/quickstart#create_a_device_registry)  
Use `demo1` for Device name, and `demo-topic` for Topic name. 
3. [Add a device to the registry](https://cloud.google.com/iot/docs/quickstart#add_a_device_to_the_registry)
To get the ES256 key of the HW crypto run `python3 /usr/lib/python3/dist-packages/coral/cloudiot/ecc608_pubkey.py`
4. Configure the cloud config
Edit the cloud_config.ini in the edge folder to ProjectID, RegistryID, and DeviceID set in step 2. Enable Cloud IoT core by setting Enabled = true.
5. Install root certificate
```
$ wget https://pki.goog/roots.pem
```

## How to use
Run the following commands, then open browser.

```
export DEMO_FILES="$HOME/demo_files"
python3 detect_cloudiot.py \
  --cloud_config cloud_config.ini \
  --model ${DEMO_FILES}/mobilenet_ssd_v1_coco_quant_postprocess_edgetpu.tflite \
  --labels ${DEMO_FILES}/coco_labels.txt \
  --threshold 0.4 \
  --filter person
```

## Clean up
If you want to delete Device registry, go to IoT Core console, select the registry and click **DELETE REGISTRY** button on the top.
