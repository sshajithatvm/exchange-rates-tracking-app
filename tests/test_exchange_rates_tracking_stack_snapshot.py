'''
Snapshot test.
'''
import aws_cdk as core
import aws_cdk.assertions as assertions
from exchange_rates_tracking.exchange_rates_tracking_stack import ExchangeRatesTrackingStack


def test_matches_snapshot(snapshot):
    '''
    Test snapshot.
    '''
    app = core.App()
    stack = ExchangeRatesTrackingStack(app, 'exchange-rates-tracking')
    template = assertions.Template.from_stack(stack)
    assert template.to_json() == snapshot
