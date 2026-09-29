"""Unique url slugs for talkgroups

Talkgroup pages are /tg/<slug>/, the slug comes from the alpha tag. Two
radio systems can use the same alpha tag, so the later one gets the
system name added. Also used by the 0064 migration, so no model imports.
"""
import re
from itertools import count

from django.utils.text import slugify


def slug_candidates(alpha_tag, dec_id, system_name):
    base = slugify(alpha_tag) or 'tg-{}'.format(dec_id)
    system = slugify(system_name) or 'system'
    yield base
    yield '{}-{}'.format(base, system)
    yield '{}-{}-{}'.format(base, system, dec_id)
    for number in count(2):
        yield '{}-{}'.format(base, number)


def is_candidate(slug, alpha_tag, dec_id, system_name):
    """Is slug one this talkgroup could have been given"""
    if not slug:
        return False
    candidates = slug_candidates(alpha_tag, dec_id, system_name)
    fixed = [next(candidates) for _ in range(3)]
    return slug in fixed or re.fullmatch(re.escape(fixed[0]) + r'-\d+', slug) is not None


def unique_talkgroup_slug(queryset, pk, alpha_tag, dec_id, system_name, current_slug=None):
    """Pick the slug for a talkgroup, queryset is all talkgroups

    Keeps current_slug when it still fits the alpha tag and nobody else
    has it, so urls do not change on every save.
    """
    others = queryset.exclude(pk=pk) if pk else queryset
    if is_candidate(current_slug, alpha_tag, dec_id, system_name) and not others.filter(slug=current_slug).exists():
        return current_slug
    for slug in slug_candidates(alpha_tag, dec_id, system_name):
        if not others.filter(slug=slug).exists():
            return slug
