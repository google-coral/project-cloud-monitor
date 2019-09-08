# Realtime WebUI monitor on GAE
In this part, you will make a WebUI running on GAE(Google App Engine).

## Prerequisites
If you didn't complete instruction at `/edge`, `/dataflow`, complete them first.

### Change settings
If you have changed IoT Core device name and/or Firebase collection name in the previous instruction, you can change them in `app.yaml`.

## Deploy GAE application
On Cloud Shell, go to the directory `/webui` if you are not.
Then type following command to deploy.
```
$ gcloud app deploy .
```

It takes several minutes. You may be asked some questions during deployment, choose your desired options.

## How to use
To use this demo, first open https://PROJECTID.appspot.com/ on your browser. This is the webUI that shows object detection results in real-time.

## Clean up
App Engine has [28 frontend instance hours per day](https://cloud.google.com/free/docs/gcp-free-tier#always-free-usage-limits) free tier, usually this is enough to keep running your app without any charge though, if you want to avoid unneccesary consumption, you can disable or delete your App Engine.

To disable your App Engine, go to [App Engine settings](https://console.cloud.google.com/appengine/settings) and click **Disable Application** button. Once you disable your App Engine, you can also delete it if you want.
 