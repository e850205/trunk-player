# San Diego-Imperial County RCS NextGen talkgroups

Talkgroup labels, agencies and cities for the RCS NextGen P25 system (RadioReference system 10521),
built from the RadioReference talkgroup listing on 2026-10-02.

* `talkgroups.csv` - alpha tag, description, service tag and mode from RadioReference. The agency is the
  RadioReference category; city categories are split into `<City> Police Department`, `<City> Fire Department`,
  `<City> Lifeguards` and `City of <City>`. The city is the category's city, or the one place named in the
  description of a countywide talkgroup (e.g. Sheriff station dispatch).
* `cities.csv` - the police and fire agency serving each city. Contract cities use the County Sheriff, and cities
  without their own fire department use their fire dispatch zone.

Load them (system 0 here) with:

    ./manage.py import_directory --system 0 --talkgroups utility/directories/san-diego-rcs/talkgroups.csv --cities utility/directories/san-diego-rcs/cities.csv

Talkgroup 2776 is listed twice on RadioReference (Rainbow MWD and Westmorland Wastewater); the last one wins.
