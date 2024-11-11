'''
Lambda function code for updating exchanges rates in Dynamodb table.
'''
import os
import sys
import logging
import urllib.error
import urllib.request
from datetime import datetime
import xml.etree.ElementTree as ET

import boto3

# Exchange rates XML file download link
DOWNLOAD_URL = 'https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml'

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
    Update exchange rates in database.
    '''
    LOGGER.info('Getting exchange rates data from European Central Bank')
    date, exchange_rates = get_exchange_rates()
    LOGGER.info('Updating exchange rates in database')
    update_exchange_rates(date, exchange_rates)
    LOGGER.info('Job completed')


def update_exchange_rates(date, exchange_rates):
    '''
    Update exchange rates in database.
    '''
    dynamodb = boto3.resource('dynamodb', endpoint_url=ENDPOINT_URL)
    table = dynamodb.Table(TABLE_NAME)
    # Batch write to database
    with table.batch_writer() as writer:
        # Exchange rates
        for currency, data in exchange_rates.items():
            data['id'] = currency
            writer.put_item(Item=data)
        # Dates
        writer.put_item(Item={'id': 'publish_date', 'value': date})
        writer.put_item(Item={'id': 'update_date', 'value': datetime.utcnow().strftime('%Y-%m-%d')})


def get_exchange_rates():
    '''
    Get exchange rate data (current and difference) from European Central Bank.
    '''
    # Download XML file having exchange rates data
    try:
        response = urllib.request.urlopen(DOWNLOAD_URL, timeout=30)
    except urllib.error.URLError as err:
        LOGGER.critical('Failed to download exchange rates data from %s', DOWNLOAD_URL)
        LOGGER.critical(err)
        sys.exit(1)
    xml_data = response.read()
    # Parser XML and read exchange rates of last 2 days
    data = []
    doc = ET.fromstring(xml_data)
    for i, x in enumerate(doc.find('{http://www.ecb.int/vocabulary/2002-08-01/eurofxref}Cube')):
        daily_data = {
            'date': x.attrib['time'].strip(),
            'rates': {y.attrib['currency'].strip(): y.attrib['rate'].strip() for y in x}
        }
        data.append(daily_data)
        if i == 1:
            break
    # Log error and exit if data parsing fails
    if len(data) < 2:
        LOGGER.critical('Failed to read exchange rates from XML: %s', DOWNLOAD_URL)
        sys.exit(1)
    # Latest rates
    date = data[0]['date']
    latest_rates = data[0]['rates']
    # Previous day rates
    previous_rates = data[1]['rates']
    # Exchange rates document with current rates and difference
    exchange_rates = {}
    for currency, rate in latest_rates.items():
        if currency not in previous_rates:
            continue
        # Previous rate
        p_rate = float(previous_rates[currency])
        # Difference
        diff = float(rate) - p_rate
        diff = round(diff, 4) or 0.0
        # Difference in percentage
        diff_percent = (diff / p_rate) * 100
        diff_percent = round(diff_percent, 4) or 0.0
        # Add sign to difference and percentage
        diff = f'+{diff}' if diff > 0 else f'{diff}'
        diff_percent = f'+{diff_percent} %' if diff_percent > 0 else f'{diff_percent} %'
        exchange_rates[currency] = {'value': rate, 'diff': diff, 'diff_percent': diff_percent}
    return date, exchange_rates
