# Azure opentelemetry integration

import os
import logging
from azure.monitor.opentelemetry import configure_azure_monitor

# create a dedicated logger
logger = logging.getLogger("Brand-Guardian-Telemetry")

def setup_telemetry():
    '''
    Initialize Azure Monitor OpenTelemetry
    Tracks : HTTP requests, database queries, errors, performance matrics
    send this data to azure monitor

    It auto capture every API requests
    No need to manually log each endpoint
    '''
    # retrieve connection string
    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    # check if configured
    if not connection_string:
        logger.warning("No Instrumentation key found. Telemetry is DISABLED")
        return
    # configure the azure monitor
    try:
        configure_azure_monitor(
            connection_string = connection_string,
            logger_name = "brand-guardian-tracer"
        )
        logger.info("Azure Tracking Enabled and Connected")
    except Exception as e:
        logger.error(f"Failed to Initialize Azure Monitor: {e}")


'''
why do use telemetry here?

Without it:
API is slow -> No idea which part is slow or problem with
How many users using it today? No visibility

With :
/audit endpoint average 4.5 sec (Indexer takes 3.8 sec)
Error logs show: 12% of audit fail due to youtube download errors
Metrics show: 450 api calls todays, 89 % success rate

'''