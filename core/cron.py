import logging
from django.core.management import call_command
from django_cron import CronJobBase, Schedule
# Sync Sellers at 9 AM (once daily)


# class SyncSellersCronJob(CronJobBase):
#     RUN_AT_TIMES = ['09:00']  # KSA time (Asia/Riyadh)

#     schedule = Schedule(run_at_times=RUN_AT_TIMES)
#     code = 'core.sync_sellers_cron'

#     def do(self):
#         logging.info("Running Sync Sellers Cron Job")
#         call_command('sync_sellers')


class SyncSellersCronJob(CronJobBase):
    RUN_EVERY_MINS = 120  # Run every 5 minutes
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'core.sync_sellers_cron'

    def do(self):
        logging.info("Running Sync Sellers Cron Job")
        call_command('sync_sellers')


# Sync Orders every 25 minutes
class SyncOrdersCronJob(CronJobBase):
    RUN_EVERY_MINS = 25  # Run every 30 minutes
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'core.sync_orders_cron'

    def do(self):
        logging.info("Running Sync Orders Cron Job")
        call_command('sync_orders')


# Sync Bills every 35 minutes
class SyncBillsCronJob(CronJobBase):
    RUN_EVERY_MINS = 35  # Run every 30 minutes
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'core.sync_bills_cron'

    def do(self):
        logging.info("Running Sync Bills Cron Job")
        call_command('sync_bills')
