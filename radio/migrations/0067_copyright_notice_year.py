from django.db import migrations


def use_current_year(apps, schema_editor):
    """The default notice was 'Copyright 2019', show the current year instead
    (only when it was never changed)"""
    SiteOption = apps.get_model('radio', 'SiteOption')
    SiteOption.objects.filter(name='COPYRIGHT_NOTICE', value='Copyright 2019').update(
        value='Copyright {year}',
        description='Page footer, {year} shows the current year')


class Migration(migrations.Migration):

    dependencies = [
        ('radio', '0066_transmission_duplicate_of'),
    ]

    operations = [
        migrations.RunPython(use_current_year, migrations.RunPython.noop),
    ]
