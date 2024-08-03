# -*- coding: utf-8 -*-

import math
from collections import defaultdict
from datetime import datetime, time, timedelta
from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrule, DAILY, WEEKLY
from pytz import timezone, utc
from odoo import fields, models, api, _
from odoo.osv import expression
from odoo.tools.float_utils import float_round
from odoo.addons.resource.models.resource import make_aware, Intervals


def float_to_time(hours):
    """ Convert a number of hours into a time object. """
    if hours == 24.0:
        return time.max
    fractional, integral = math.modf(hours)
    return time(int(integral), int(float_round(60 * fractional, precision_digits=0)), 0)


class ResourceCalendarAttendance(models.Model):
    _inherit = 'resource.calendar.attendance'

    is_weekend = fields.Boolean(string="Is Weekend", default=False)


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    def _attendance_intervals_batch(self, start_dt, end_dt, resources=None, domain=None, tz=None):
        """ Return the attendance intervals in the given datetime range.
            The returned intervals are expressed in specified tz or in the resource's timezone.
        """
        self.ensure_one()
        resources = self.env['resource.resource'] if not resources else resources
        assert start_dt.tzinfo and end_dt.tzinfo
        self.ensure_one()
        combine = datetime.combine

        resources_list = list(resources) + [self.env['resource.resource']]
        resource_ids = [r.id for r in resources_list]
        domain = domain if domain is not None else []
        domain = expression.AND([domain, [
            ('calendar_id', '=', self.id),
            ('resource_id', 'in', resource_ids),
            ('display_type', '=', False),
            ('is_weekend', '=', False),
        ]])

        # for each attendance spec, generate the intervals in the date range
        cache_dates = defaultdict(dict)
        cache_deltas = defaultdict(dict)
        result = defaultdict(list)
        for attendance in self.env['resource.calendar.attendance'].search(domain):
            for resource in resources_list:
                # express all dates and times in specified tz or in the resource's timezone
                tz = tz if tz else timezone((resource or self).tz)
                if (tz, start_dt) in cache_dates:
                    start = cache_dates[(tz, start_dt)]
                else:
                    start = start_dt.astimezone(tz)
                    cache_dates[(tz, start_dt)] = start
                if (tz, end_dt) in cache_dates:
                    end = cache_dates[(tz, end_dt)]
                else:
                    end = end_dt.astimezone(tz)
                    cache_dates[(tz, end_dt)] = end

                start = start.date()
                if attendance.date_from:
                    start = max(start, attendance.date_from)
                until = end.date()
                if attendance.date_to:
                    until = min(until, attendance.date_to)
                if attendance.week_type:
                    start_week_type = self.env['resource.calendar.attendance'].get_week_type(start)
                    if start_week_type != int(attendance.week_type):
                        # start must be the week of the attendance
                        # if it's not the case, we must remove one week
                        start = start + relativedelta(weeks=-1)
                weekday = int(attendance.dayofweek)

                if self.two_weeks_calendar and attendance.week_type:
                    days = rrule(WEEKLY, start, interval=2, until=until, byweekday=weekday)
                else:
                    days = rrule(DAILY, start, until=until, byweekday=weekday)

                for day in days:
                    # attendance hours are interpreted in the resource's timezone
                    hour_from = attendance.hour_from
                    if (tz, day, hour_from) in cache_deltas:
                        dt0 = cache_deltas[(tz, day, hour_from)]
                    else:
                        dt0 = tz.localize(combine(day, float_to_time(hour_from)))
                        cache_deltas[(tz, day, hour_from)] = dt0

                    hour_to = attendance.hour_to
                    if (tz, day, hour_to) in cache_deltas:
                        dt1 = cache_deltas[(tz, day, hour_to)]
                    else:
                        dt1 = tz.localize(combine(day, float_to_time(hour_to)))
                        cache_deltas[(tz, day, hour_to)] = dt1
                    result[resource.id].append((max(cache_dates[(tz, start_dt)], dt0), min(cache_dates[(tz, end_dt)], dt1), attendance))
        return {r.id: Intervals(result[r.id]) for r in resources_list}

    def _attendance_all_intervals_batch(self, start_dt, end_dt, resources=None, domain=None, tz=None):
        """ Return the attendance intervals in the given datetime range.
            The returned intervals are expressed in specified tz or in the resource's timezone.
        """
        self.ensure_one()
        resources = self.env['resource.resource'] if not resources else resources
        assert start_dt.tzinfo and end_dt.tzinfo
        self.ensure_one()
        combine = datetime.combine

        resources_list = list(resources) + [self.env['resource.resource']]
        resource_ids = [r.id for r in resources_list]
        domain = domain if domain is not None else []
        domain = expression.AND([domain, [
            ('calendar_id', '=', self.id),
            ('resource_id', 'in', resource_ids),
            ('display_type', '=', False),
        ]])

        # for each attendance spec, generate the intervals in the date range
        cache_dates = defaultdict(dict)
        cache_deltas = defaultdict(dict)
        result = defaultdict(list)
        for attendance in self.env['resource.calendar.attendance'].search(domain):
            for resource in resources_list:
                # express all dates and times in specified tz or in the resource's timezone
                tz = tz if tz else timezone((resource or self).tz)
                if (tz, start_dt) in cache_dates:
                    start = cache_dates[(tz, start_dt)]
                else:
                    start = start_dt.astimezone(tz)
                    cache_dates[(tz, start_dt)] = start
                if (tz, end_dt) in cache_dates:
                    end = cache_dates[(tz, end_dt)]
                else:
                    end = end_dt.astimezone(tz)
                    cache_dates[(tz, end_dt)] = end

                start = start.date()
                if attendance.date_from:
                    start = max(start, attendance.date_from)
                until = end.date()
                if attendance.date_to:
                    until = min(until, attendance.date_to)
                if attendance.week_type:
                    start_week_type = self.env['resource.calendar.attendance'].get_week_type(start)
                    if start_week_type != int(attendance.week_type):
                        # start must be the week of the attendance
                        # if it's not the case, we must remove one week
                        start = start + relativedelta(weeks=-1)
                weekday = int(attendance.dayofweek)

                if self.two_weeks_calendar and attendance.week_type:
                    days = rrule(WEEKLY, start, interval=2, until=until, byweekday=weekday)
                else:
                    days = rrule(DAILY, start, until=until, byweekday=weekday)

                for day in days:
                    # attendance hours are interpreted in the resource's timezone
                    hour_from = attendance.hour_from
                    if (tz, day, hour_from) in cache_deltas:
                        dt0 = cache_deltas[(tz, day, hour_from)]
                    else:
                        dt0 = tz.localize(combine(day, float_to_time(hour_from)))
                        cache_deltas[(tz, day, hour_from)] = dt0

                    hour_to = attendance.hour_to
                    if (tz, day, hour_to) in cache_deltas:
                        dt1 = cache_deltas[(tz, day, hour_to)]
                    else:
                        dt1 = tz.localize(combine(day, float_to_time(hour_to)))
                        cache_deltas[(tz, day, hour_to)] = dt1
                    result[resource.id].append((max(cache_dates[(tz, start_dt)], dt0), min(cache_dates[(tz, end_dt)], dt1), attendance))
        return {r.id: Intervals(result[r.id]) for r in resources_list}

    def get_all_work_duration_data(self, from_datetime, to_datetime, domain=None):
        from_datetime, dummy = make_aware(from_datetime)
        to_datetime, dummy = make_aware(to_datetime)
        day_total = self._get_all_resources_day_total(from_datetime, to_datetime)[False]
        # actual hours per day
        intervals = self._attendance_all_intervals_batch(from_datetime, to_datetime, domain=domain)[False]
        return self._get_days_data(intervals, day_total)

    def _get_all_resources_day_total(self, from_datetime, to_datetime, resources=None):
        self.ensure_one()
        resources = self.env['resource.resource'] if not resources else resources
        resources_list = list(resources) + [self.env['resource.resource']]
        # total hours per day:  retrieve attendances with one extra day margin,
        # in order to compute the total hours on the first and last days
        from_full = from_datetime - timedelta(days=1)
        to_full = to_datetime + timedelta(days=1)
        intervals = self._attendance_all_intervals_batch(from_full, to_full, resources=resources)

        result = defaultdict(lambda: defaultdict(float))
        for resource in resources_list:
            day_total = result[resource.id]
            for start, stop, meta in intervals[resource.id]:
                day_total[start.date()] += (stop - start).total_seconds() / 3600
        return result
