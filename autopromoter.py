#!/usr/bin/python

import os
import argparse
import sys
import plistlib
import datetime

DEFAULT_DAYS = 5
DEFAULT_CATS = ['development', 'testing', 'production']

def update_catalogs_per_prodems(catalogs, prodems, now_base=datetime.datetime.now()):
	prodem_catalogs = set([i.get('catalog') for i in prodems])
	catalogs = set(catalogs)

	# check for any non-policy catalogs and warn user
	addl_catalogs = catalogs.difference(prodem_catalogs)
	if addl_catalogs:
		print 'WARNING: additional catalogs found in pkginfo that are not in the'
		print '         promotion/demotion set:'
		print '           ' + ', '.join(addl_catalogs)
		print '         please remove catalog(s) from pkginfo file if not desired'

	# start building the current set of managed pro/dem catalogs by including
	# non-managed catalogs
	cur_catalogs = list(addl_catalogs)

	cats_changed = False

	# the meat and potatoes:
	# analyze the promotion & demotion timestamps, compare them with our
	# current now() timestamp and decide whether catalogs should be active
	# in the pkginfo or not. contrast against existing pkginfo to see if
	# there are changes
	for pd in prodems:
		if not isinstance(pd.get('demotion_date'), datetime.datetime):
			# faux demotion date that never expires (is a day in the future)
			demotion_date = now_base + datetime.timedelta(days=1)
		else:
			demotion_date = pd['demotion_date']
		if not isinstance(pd.get('promotion_date'), datetime.datetime):
			# faux promotion that's always promoted (is a day in the past)
			promotion_date = now_base - datetime.timedelta(days=1)
		else:
			promotion_date = pd['promotion_date']

		if now_base >= promotion_date and now_base < demotion_date:
			cur_catalogs.append(pd['catalog'])

			if not pd['catalog'] in catalogs:
				print 'catalog %s ought to be active now: promoting' % pd['catalog']
				cats_changed = True
		else:
			if pd['catalog'] in catalogs:
				print 'catalog %s should not be active now: demoting' % pd['catalog']
				cats_changed = True

	if cats_changed:
		return cur_catalogs
	else:
		print 'no catalog promotions or demotions'
		return None


def pkginfo_catalog_prodem(pkginfo_fn, catdurs, keep_catalogs=False):
	print 'processing pkginfo "%s"%s...' % (pkginfo_fn, ' keeping catalogs' if keep_catalogs else '')

	plist_changed = False
	pkginfo_d = plistlib.readPlist(pkginfo_fn)

	if '_metadata' not in pkginfo_d.keys():
		# create _metadata key if it doesn't exist. this is to catch older
		# pkginfos that didn't automatically generate this field
		pkginfo_d['_metadata'] = {}
		plist_changed = True

	if 'catalog_promotion' not in pkginfo_d['_metadata'].keys():
		pkginfo_d['_metadata']['catalog_promotion'] = []
		plist_changed = True

	prodems = pkginfo_d['_metadata']['catalog_promotion']

	# cache a copy of now() so it doesn't update on us while we process
	now_base = datetime.datetime.now()

	for i, (catdur_name, catdur_days) in enumerate(catdurs):
		# we're searching on a catalog-by-catalog basis for the set of pro/dem
		# catalogs in case future policy changes (i.e. diff. catalogs or dates)
		# are adjusted on the CLI. this could be much easier if we only
		# supported setting the pro/dem set once and then had the munki admin
		# make any future adjustments. up for discussion.

		# find index of pkginfo promotion/demotion set that matches the
		# current "policy" promotion/demotion set. this is so we know we
		# have the initial data for each catalog in the pkginfo or not
		found_prodem = False
		for j, prodem in enumerate(prodems):
			if catdur_name == prodem['catalog']:
				found_prodem = True
				break

		if not found_prodem:
			print 'creating initial promotion/demotion record for catalog %s' % catdur_name

			# if this catalog is the first in our list promote/demote list..
			new_prodem = {'catalog': catdur_name, 'creation_date': now_base}
			if i == 0:
				# first item in existing promotion/demotion set
				# only needs a demotion date (first step)
				new_prodem['demotion_date'] = now_base + datetime.timedelta(days=catdur_days)

				print '  promoting on: (now until demotion)'
				print '  demoting on: ', new_prodem['demotion_date'], '(+%d days from now)' % catdur_days
			elif i > 0 and i < (len(catdurs) - 1):
				# a middle item in existing promotion/demotion set
				# needs promotion and demotion date (middle steps)
				new_prodem['promotion_date'] = prodems[-1]['demotion_date']
				new_prodem['demotion_date'] = prodems[-1]['demotion_date'] + datetime.timedelta(days=catdur_days)

				print '  promoting on:', new_prodem['promotion_date'], '(same as prev. cat demotion)'
				print '  demoting on: ', new_prodem['demotion_date'], '(+%d days from prev. cat demotion)' % catdur_days
			elif i == len(catdurs) - 1:
				# last item in existing promotion/demotion set
				# only needs a promotion date (last step)
				new_prodem['promotion_date'] = prodems[-1]['demotion_date']

				print '  promoting on:', new_prodem['promotion_date'], '(same as prev. cat demotion)'
				print '  demoting on: (never after promotion)'

			prodems.append(new_prodem)
			plist_changed = True

	changed_cats = update_catalogs_per_prodems(pkginfo_d['catalogs'], prodems, now_base)

	if changed_cats:
		pkginfo_d['catalogs'] = changed_cats
		plist_changed = True

	if plist_changed:
		print 'writing changed pkginfo'
		plistlib.writePlist(pkginfo_d, pkginfo_fn)

def main():
	parser = argparse.ArgumentParser(description='Munki pkginfo catalog promotion & demotion manager')
	parser.add_argument('pkginfo', nargs='+', help='filename(s) of pkginfo file(s)')
	# parser.add_argument('--keep', action='store_true',
	# 	help='ignore demotion dates for catalogs. this keeps catalogs listed '
	# 	     'in the pkginfo (never demoting them)')
	parser.add_argument('--catalog', metavar='cat[:days]', action='append',
		help='name of catalogs and optional demotion/promotion duration in '
		     'number of days ("--catalog testing:14"). note only sets duration'
		     'dates once for a pkginfo')

	args = parser.parse_args()
	
	for pkginfo in args.pkginfo:
		if not os.path.isfile(pkginfo):
			print 'pkginfo "%s" is not a file' % pkginfo
			return 1

	# get list of catalogs in tuple of (catname, days)
	catdurlist = []
	if args.catalog:
		for catdur in [x.split(':') for x in args.catalog]:
			if len(catdur) == 2:
				catdurlist.append((catdur[0], int(catdur[1]), ))
			elif len(catdur) == 1:
				# no days specified, let's assume default
				catdurlist.append((catdur[0], DEFAULT_DAYS, ))
			else:
				print 'invalid catalog days specified, must be "catalog[:days]" like "testing:25"'
				return 1
	else:
		for cat in DEFAULT_CATS:
			catdurlist.append((cat, DEFAULT_DAYS, ))

	for pkginfo in args.pkginfo:
		pkginfo_catalog_prodem(pkginfo, catdurlist) # , args.keep)

	return 0

if __name__ == '__main__':
	sys.exit(int(main()))
