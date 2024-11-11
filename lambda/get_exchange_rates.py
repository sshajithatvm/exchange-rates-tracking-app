'''
Lambda function code for fetching exchange rates from Dynamodb table.
'''
import os
import json
import logging

import boto3

# Logger
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

# Dynamodb table name
TABLE_NAME = os.environ['TABLE_NAME']

# Endpoint URL, required for execution on localstack
if 'LOCALSTACK_HOSTNAME' in os.environ:
    ENDPOINT_URL = f'http://{os.environ["LOCALSTACK_HOSTNAME"]}:4566'
else:
    ENDPOINT_URL = None


def handler(event, context):
    '''
    Read exchanges rates of tracked currencies from the database.
    '''
    # Read exchange rates from database
    LOGGER.info('Reading exchange rates from database')
    items = read_from_db()
    # Return if database is empty
    if not items:
        LOGGER.info('No data available')
        error = "No data available, please try later"
        return {'statusCode': 200, 'body': json.dumps({'error': error}, indent=4)}
    # Construct response
    LOGGER.info('Constructing response')
    response = {'update_date': 'N/A', 'publish_date': 'N/A', 'base_currency': 'EUR', 'exchange_rates': []}
    for item in items:
        if item['id'] in ('update_date', 'publish_date'):
            response[item['id']] = item['value']
        else:
            data = {'currency':          item['id'],
                    'rate':              item['value'],
                    'change':            item['diff'],
                    'change_percentage': item['diff_percent']}
            response['exchange_rates'].append(data)
    # Sort list by currency name
    response['exchange_rates'] = sorted(response['exchange_rates'], key=lambda x: x['currency'])
    # Return response
    return {'statusCode': 200, 'body': json.dumps(response, indent=4)}


def read_from_db():
    '''
    Read records from database.
    '''
    dynamodb = boto3.resource('dynamodb', endpoint_url=ENDPOINT_URL)
    table = dynamodb.Table(TABLE_NAME)
    # Read table data
    response = table.scan()
    items = response['Items']
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response['Items'])
    return items
