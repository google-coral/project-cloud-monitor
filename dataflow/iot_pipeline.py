"""Dataflow ETL pipeline that retrieves data from Pub/Sub
and save the data into Firestore and BigQuery.
"""
import argparse
import logging
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.options.pipeline_options import SetupOptions
from apache_beam.options.pipeline_options import StandardOptions


def run(argv=None):
  """Build and run the pipeline."""
  from google.cloud import firestore
  import json

  parser = argparse.ArgumentParser()
  parser.add_argument('--input_topic',
                      dest='input_topic',
                      required=True,
                      help='Input Pub/Sub Topic')
  parser.add_argument('--output_table',
                      dest='output_table',
                      required=True,
                      help='Output BigQuery Table')

  known_args, pipeline_args = parser.parse_known_args(argv)
  # We use the save_main_session option because one or more DoFn's in this
  # workflow rely on global context (e.g., a module imported at module level).
  pipeline_options = PipelineOptions(pipeline_args)
  pipeline_options.view_as(SetupOptions).save_main_session = True
  pipeline_options.view_as(StandardOptions).streaming = True

  p = beam.Pipeline(options=pipeline_options)

  def pubsubmessage_to_element(message):
    # convert PubsubMessage to PCollection element.
    # It seems ReadFromPubSub doesn't retrieve publishTime value from protobuf,
    # so we leave timestamp value to None here.
    # https://github.com/apache/beam/blob/master/sdks/python/apache_beam/io/gcp/pubsub.py#L102
    return {'timestamp': None,
            'device': message.attributes['deviceId'],
            'jsondata': message.data}

  def write_to_firestore(element):
    # Write PCollection element data to Firestore

    db = firestore.Client()
    doc_ref = db.collection(u'iot').document(element['device'])
    doc_ref.set(json.loads(element['jsondata']))

  messages = (p | beam.io.ReadFromPubSub(topic=known_args.input_topic,
                                         with_attributes=True)
                | beam.Map(pubsubmessage_to_element))

  (messages | 'Write to BQ' >> beam.io.gcp.bigquery.WriteToBigQuery(
                  table=known_args.output_table,
                  schema='timestamp:DATE, device:STRING, jsondata:STRING',
                  create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED,
                  write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND, batch_size=1))
  (messages | 'Write to Firestore' >> beam.Map(write_to_firestore))

  result = p.run()
  result.wait_until_finish()


if __name__ == '__main__':
  logging.getLogger().setLevel(logging.INFO)
  run()
