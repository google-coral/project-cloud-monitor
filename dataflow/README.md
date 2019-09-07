## Prerequisites

### Enable Firestore and Dataflow
Go to [API Library](https://console.cloud.google.com/apis/library), search "Firestore" and "Dataflow" by name and enable them if not enabled.

### Create Google Cloud Storage Bucket
1. Go to [GCS Console](https://console.cloud.google.com/storage) and click "**CREATE BUCKET**" on the top.
2. Choose Bucket name as you wish, leave default for the other options.

*remember this bucket name. you will need it in the following step.

### Create Firestore 
1. Go to https://console.cloud.google.com/firestore and select “**SELECT NATIVE MODE**”.
2. Select your desired region and then click “**CREATE DATABASE**”
3. Once created, make document named `iot`

### Link GCP Project and Firebase Project
1. Go to https://console.firebase.google.com/ and click “**Add project**”, then select your GCP project.
2. Change Firestore security rules  
Once you create Firebase project, go to Database menu on left side-menu, then click “**Rules**” tab.
Change read and write rule from false to true on the line 4
```
allow read, write: if true;
```

### Setup deployment environment  
To deploy Dataflow pipeline, you must setup required libraries on Cloud Shell.
Clone repository into your Cloud Shell environment, change directory to `/dataflow`
Then type following command to install required libraries.
```
$ pip3 install apache-beam[gcp] google-cloud-firestore
```

### Create BigQuery dataset and table
Create dataset and table as following

dataset: `iot_demo`  
table: `iot_demo_chunk`  
schema: `timestamp:DATE, device:STRING, jsondata:STRING`  

You can make these dataset and table with following `bq` commands.
```
$ bq mk iot_demo
$ bq mk -t iot_demo.iot_demo_chunk timestamp:DATE,device:STRING,jsondata:STRING
```

## Deploy the pipeline
Type following command. Once the command finished, your pipeline is deployed on GCP environment.

```
$ export PROJECT_ID='your project id'
$ export BUCKET='your GCP bucket'
$ python3 iot_pipeline.py \
    --job_name iot-pipeline \
    --runner DataflowRunner \
    --project ${PROJECT_ID} \
    --region us-central1 \
    --requirements_file requirements.txt \
    --staging_location gs://${BUCKET}/staging \
    --temp_location gs://${BUCKET}/temp \
    --input_topic projects/${PROJECT_ID}/topics/demo-topic \
    --output_table iot_demo.iot_demo_chunk
```

To check if your pipeline is deployed, go to [Dataflow console](https://console.cloud.google.com/dataflow)

**Note:**  
The pipeline **remains running** until you shutdown. To avoid unnecessary consumption, do not forget to shutdown Dataflow pipeline after you use (simply you just click “cancel” button on the pipeline console)
