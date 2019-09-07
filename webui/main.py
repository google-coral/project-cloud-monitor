from flask import Flask, render_template
import os

app = Flask(__name__)
PROJECTID = os.getenv('GOOGLE_CLOUD_PROJECT')
IOT_DEVICEID = os.getenv('IOT_DEVICEID')
FB_COLLECTION = os.getenv('FB_COLLECTION')


@app.route('/', methods=['GET'])
def index():
    param = {"project_id": PROJECTID,
             "device_id": IOT_DEVICEID,
             "collection": FB_COLLECTION}
    return render_template('index.html', **param)


# if __name__ == '__main__':
#     app.run(host='127.0.0.1', port=8080, debug=True)
if __name__ == '__main__':
    app.run(debug=True)
