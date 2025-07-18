import logging
from django_cron import CronJobBase, Schedule
from django.core.management import call_command

# Sync Sellers at 9 AM (once daily)


class SyncSellersCronJob(CronJobBase):
    RUN_AT_TIMES = ['09:00']  # KSA time (Asia/Riyadh)

    schedule = Schedule(run_at_times=RUN_AT_TIMES)
    code = 'core.sync_sellers_cron'

    def do(self):
        logging.info("Running Sync Sellers Cron Job")
        call_command('sync_sellers')


# Sync Orders every 30 minutes
class SyncOrdersCronJob(CronJobBase):
    schedule = Schedule(run_every_mins=30)
    code = 'core.sync_orders_cron'

    def do(self):
        logging.info("Running Sync Orders Cron Job")
        call_command('sync_orders')


# Sync Bills every 40 minutes
class SyncBillsCronJob(CronJobBase):
    schedule = Schedule(run_every_mins=40)
    code = 'core.sync_bills_cron'

    def do(self):
        logging.info("Running Sync Bills Cron Job")
        call_command('sync_bills')
