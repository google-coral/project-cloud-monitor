"""A demo which runs object detection on camera frames.
"""
# [START iot_mqtt_includes]
import datetime
import os
import ssl
import time
import jwt
import paho.mqtt.client as mqtt
# [END iot_mqtt_includes]

import argparse
import collections
import colorsys
import itertools
import time
from edgetpu.detection.engine import DetectionEngine
from edgetpuvision import svg
from edgetpuvision import utils
from edgetpuvision.apps import run_app, run_server

# The initial backoff time after a disconnection occurs, in seconds.
minimum_backoff_time = 1

# The maximum backoff time before giving up, in seconds.
MAXIMUM_BACKOFF_TIME = 32

# Whether to wait with exponential backoff before publishing.
should_backoff = False

# MQTT settings, change if needed
ALGORITHM = 'RS256'
MQTT_BRIDGE_HOSTNAME = 'mqtt.googleapis.com'
MQTT_BRIDGE_PORT = 8883
PRIVATE_KEY_FILE = '/home/mendel/rsa_private.pem'
CA_CERTS = '/home/mendel/roots.pem'
JWT_EXPIRES_MINUTES = 20
MESSAGE_TYPE = 'event'

# Cloud IoT settings
CLOUD_REGION = 'us-central1'
DEVICE_ID = 'demo1'
REGISTRY_ID = 'demo-registry'


# [START iot_mqtt_jwt]
def create_jwt(project_id, private_key_file, algorithm):
    """Creates a JWT (https://jwt.io) to establish an MQTT connection.
        Args:
         project_id: The cloud project ID this device belongs to
         private_key_file: A path to a file containing either an RSA256 or
                 ES256 private key.
         algorithm: The encryption algorithm to use. Either 'RS256' or 'ES256'
        Returns:
            An MQTT generated from the given project_id and private key, which
            expires in 20 minutes. After 20 minutes, your client will be
            disconnected, and a new JWT will have to be generated.
        Raises:
            ValueError: If the private_key_file does not contain a known key.
        """

    token = {
            # The time that the token was issued at
            'iat': datetime.datetime.utcnow(),
            # The time the token expires.
            'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=60),
            # The audience field should always be set to the GCP project id.
            'aud': project_id
    }

    # Read the private key file.
    with open(private_key_file, 'r') as f:
        private_key = f.read()

    print('Creating JWT using {} from private key file {}'.format(
            algorithm, private_key_file))

    return jwt.encode(token, private_key, algorithm=algorithm)
# [END iot_mqtt_jwt]


# [START iot_mqtt_config]
def error_str(rc):
    """Convert a Paho error to a human readable string."""
    return '{}: {}'.format(rc, mqtt.error_string(rc))


def on_connect(unused_client, unused_userdata, unused_flags, rc):
    """Callback for when a device connects."""
    print('on_connect', mqtt.connack_string(rc))

    # After a successful connect, reset backoff time and stop backing off.
    global should_backoff
    global minimum_backoff_time
    should_backoff = False
    minimum_backoff_time = 1


def on_disconnect(unused_client, unused_userdata, rc):
    """Paho callback for when a device disconnects."""
    print('on_disconnect', error_str(rc))

    # Since a disconnect occurred, the next loop iteration will wait with
    # exponential backoff.
    global should_backoff
    should_backoff = True


def on_publish(unused_client, unused_userdata, unused_mid):
    """Paho callback when a message is sent to the broker."""
    print('on_publish')


def on_message(unused_client, unused_userdata, message):
    """Callback when the device receives a message on a subscription."""
    payload = str(message.payload)
    print('Received message \'{}\' on topic \'{}\' with Qos {}'.format(
            payload, message.topic, str(message.qos)))


def get_client(
        project_id, cloud_region, registry_id, device_id, private_key_file,
        algorithm, ca_certs, mqtt_bridge_hostname, mqtt_bridge_port):
    """Create our MQTT client. The client_id is a unique string that identifies
    this device. For Google Cloud IoT Core, it must be in the format below."""
    client = mqtt.Client(
      client_id=('projects/{}/locations/{}/registries/{}/devices/{}'
                  .format(
                          project_id,
                          cloud_region,
                          registry_id,
                          device_id)))

    # With Google Cloud IoT Core, the username field is ignored, and the
    # password field is used to transmit a JWT to authorize the device.
    client.username_pw_set(username='unused',
                           password=create_jwt(
                               project_id, private_key_file, algorithm))

    # Enable SSL/TLS support.
    client.tls_set(ca_certs=ca_certs, tls_version=ssl.PROTOCOL_TLSv1_2)

    # Register message callbacks. https://eclipse.org/paho/clients/python/docs/
    # describes additional callbacks that Paho supports. In this example, the
    # callbacks just print to standard out.
    client.on_connect = on_connect
    client.on_publish = on_publish
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    # Connect to the Google MQTT bridge.
    client.connect(mqtt_bridge_hostname, mqtt_bridge_port)

    # This is the topic that the device will receive configuration updates on.
    mqtt_config_topic = '/devices/{}/config'.format(device_id)

    # Subscribe to the config topic.
    client.subscribe(mqtt_config_topic, qos=1)

    return client
# [END iot_mqtt_config]


CSS_STYLES = str(svg.CssStyle({'.back': svg.Style(fill='black',
                                                  stroke='black',
                                                  stroke_width='0.5em'),
                               '.bbox': svg.Style(fill_opacity=0.0,
                                                  stroke_width='0.1em')}))
BBox = collections.namedtuple('BBox', ('x', 'y', 'w', 'h'))
BBox.area = lambda self: self.w * self.h
BBox.scale = lambda self, sx, sy: BBox(x=self.x * sx, y=self.y * sy,
                                       w=self.w * sx, h=self.h * sy)
BBox.__str__ = lambda self: 'BBox(x=%.2f y=%.2f w=%.2f h=%.2f)' % self
Object = collections.namedtuple('Object', ('id', 'label', 'score', 'bbox_flat', 'bbox'))
Object.__str__ = lambda self: 'Object(id=%d, label=%s, score=%.2f, %s)' % self


def size_em(length):
    return '%sem' % str(0.6 * length)


def color(i, total):
    return tuple(int(255.0 * c) for c in colorsys.hsv_to_rgb(i / total, 1.0, 1.0))


def make_palette(keys):
    return {key : svg.rgb(color(i, len(keys))) for i, key in enumerate(keys)}


def make_get_color(color, labels):
    if color:
        return lambda obj_id: color
    if labels:
        palette = make_palette(labels.keys())
        return lambda obj_id: palette[obj_id]
    return lambda obj_id: 'white'


def overlay(title, objs, get_color, inference_time, inference_rate, layout):
    x0, y0, width, height = layout.window
    font_size = 0.03 * height
    defs = svg.Defs()
    defs += CSS_STYLES
    doc = svg.Svg(width=width, height=height,
                  viewBox='%s %s %s %s' % layout.window,
                  font_size=font_size, font_family='monospace', font_weight=500)
    doc += defs
    for obj in objs:
        percent = int(100 * obj.score)
        if obj.label:
            caption = '%d%% %s' % (percent, obj.label)
        else:
            caption = '%d%%' % percent
        x, y, w, h = obj.bbox.scale(*layout.size)
        color = get_color(obj.id)
        doc += svg.Rect(x=x, y=y, width=w, height=h,
                        style='fill:%s;fill-opacity:0.1;stroke-width:3;stroke:%s' % (color, color),
                        _class='bbox')
        doc += svg.Rect(x=x, y=y + h,
                        width=size_em(len(caption)), height='1.2em', fill=color)
        t = svg.Text(x=x, y=y + h, fill='black')
        t += svg.TSpan(caption, dy='1em')
        doc += t
    ox = x0 + 20
    oy1, oy2 = y0 + 20 + font_size, y0 + height - 20
    # Title
    if title:
        doc += svg.Rect(x=0, y=0, width=size_em(len(title)), height='1em',
                        transform='translate(%s, %s) scale(1,-1)' % (ox, oy1), _class='back')
        doc += svg.Text(title, x=ox, y=oy1, fill='white')
    # Info
    lines = [
        'Objects: %d' % len(objs),
        'Inference time: %.2f ms (%.2f fps)' % (inference_time * 1000, 1.0 / inference_time)
    ]
    for i, line in enumerate(reversed(lines)):
        y = oy2 - i * 1.7 * font_size
        doc += svg.Rect(x=0, y=0, width=size_em(len(line)), height='1em',
                        transform='translate(%s, %s) scale(1,-1)' % (ox, y),
                        _class='back')
        doc += svg.Text(line, x=ox, y=y, fill='white')
    return str(doc)


def convert(obj, labels):
    x0, y0, x1, y1 = obj.bounding_box.flatten().tolist()
    bbox_flat = obj.bounding_box.flatten().tolist()
    bbox_flat[0] *= 640.0
    bbox_flat[1] *= 360.0
    bbox_flat[2] *= 640.0
    bbox_flat[3] *= 360.0
    return Object(id=obj.label_id,
                  label=labels[obj.label_id] if labels else None,
                  score=obj.score,
                  bbox_flat=bbox_flat,
                  bbox=BBox(x=x0, y=y0, w=x1 - x0, h=y1 - y0))


def print_results(inference_rate, objs):
    print('\nInference (rate=%.2f fps):' % inference_rate)
    for i, obj in enumerate(objs):
        print('    %d: %s, area=%.2f' % (i, obj, obj.bbox.area()))


def render_gen(args):
    global minimum_backoff_time
    import json
    import random
    # Publish to the events or state topic based on the flag.
    sub_topic = 'events' if MESSAGE_TYPE == 'event' else 'state'

    mqtt_topic = '/devices/{}/{}'.format(DEVICE_ID, sub_topic)

    jwt_iat = datetime.datetime.utcnow()
    jwt_exp_mins = JWT_EXPIRES_MINUTES
    client = get_client(
        args.project_id, CLOUD_REGION, REGISTRY_ID, DEVICE_ID,
        PRIVATE_KEY_FILE, ALGORITHM, CA_CERTS,
        MQTT_BRIDGE_HOSTNAME, MQTT_BRIDGE_PORT)

    fps_counter = utils.avg_fps_counter(30)
    engines, titles = utils.make_engines(args.model, DetectionEngine)
    assert utils.same_input_image_sizes(engines)
    engines = itertools.cycle(engines)
    engine = next(engines)
    labels = utils.load_labels(args.labels) if args.labels else None
    filtered_labels = set(l.strip() for l in args.filter.split(',')) if args.filter else None
    get_color = make_get_color(args.color, labels)
    draw_overlay = True
    yield utils.input_image_size(engine)
    output = None
    mqtt_cnt = 0
    inference_time_window = collections.deque(maxlen=30)
    inference_time = 0.0

    while True:
        d = {}
        tensor, layout, command = (yield output)
        inference_rate = next(fps_counter)
        if draw_overlay:
            start = time.monotonic()
            objs = engine .DetectWithInputTensor(tensor,
                                                 threshold=args.threshold,
                                                 top_k=args.top_k)
            inference_time_ = time.monotonic() - start
            inference_time_window.append(inference_time_)
            inference_time = sum(inference_time_window) / len(inference_time_window)
            objs = [convert(obj, labels) for obj in objs]
            if labels and filtered_labels:
                objs = [obj for obj in objs if obj.label in filtered_labels]
            objs = [obj for obj in objs if args.min_area <= obj.bbox.area() <= args.max_area]
            if args.print:
                print_results(inference_rate, objs)
            for ind, obj in enumerate(objs):
                tx = obj.label
                o = {"name": tx, "points": ",".join([str(i) for i in obj.bbox_flat])}
                d[ind] = o

            title = titles[engine]
            output = overlay(title, objs, get_color, inference_time, inference_rate, layout)
        else:
            output = None
        if command == 'o':
            draw_overlay = not draw_overlay
        elif command == 'n':
            engine = next(engines)

        # Wait if backoff is required.
        if should_backoff:
            # If backoff time is too large, give up.
            if minimum_backoff_time > MAXIMUM_BACKOFF_TIME:
                print('Exceeded maximum backoff time. Giving up.')
                break

            # Otherwise, wait and connect again.
            delay = minimum_backoff_time + random.randint(0, 1000) / 1000.0
            print('Waiting for {} before reconnecting.'.format(delay))
            time.sleep(delay)
            minimum_backoff_time *= 2
            client.connect(MQTT_BRIDGE_HOSTNAME, MQTT_BRIDGE_PORT)
        payload = json.dumps(d)

        # [START iot_mqtt_jwt_refresh]
        seconds_since_issue = (datetime.datetime.utcnow() - jwt_iat).seconds
        if seconds_since_issue > 60 * jwt_exp_mins:
            print('Refreshing token after {}s'.format(seconds_since_issue))
            jwt_iat = datetime.datetime.utcnow()
            client = get_client(
                PROJECT_ID, CLOUD_REGION,
                REGISTRY_ID, DEVICE_ID, PRIVATE_KEY_FILE,
                ALGORITHM, CA_CERTS, MQTT_BRIDGE_HOSTNAME,
                MQTT_BRIDGE_PORT)
        if mqtt_cnt > 0 and mqtt_cnt % 10 == 0:
            client.loop()
            print("-" * 20)
            print(d)
            print("-" * 20)
            client.publish(mqtt_topic, payload, qos=1)
        mqtt_cnt += 1


def add_render_gen_args(parser):
    parser.add_argument('--project_id',
                        help='GCP Project ID', required=True)
    parser.add_argument('--model',
                        help='.tflite model path', required=True)
    parser.add_argument('--labels',
                        help='labels file path')
    parser.add_argument('--top_k', type=int, default=50,
                        help='Max number of objects to detect')
    parser.add_argument('--threshold', type=float, default=0.1,
                        help='Detection threshold')
    parser.add_argument('--min_area', type=float, default=0.0,
                        help='Min bounding box area')
    parser.add_argument('--max_area', type=float, default=1.0,
                        help='Max bounding box area')
    parser.add_argument('--filter', default=None,
                        help='Comma-separated list of allowed labels')
    parser.add_argument('--color', default=None,
                        help='Bounding box display color'),
    parser.add_argument('--print', default=False, action='store_true',
                        help='Print inference results')


def main():
    # Switch to run_app if you want to run the app with HDMI
    run_server(add_render_gen_args, render_gen)
    # run_app(add_render_gen_args, render_gen)


if __name__ == '__main__':
    main()
