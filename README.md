# autopromoter

Autopromoter is a tool for [Munki](https://github.com/munki/munki) [pkginfo files](https://github.com/munki/munki/wiki/Pkginfo-Files) that automatically promotes (and demotes) Munki catalogs in a given pkginfo file based on a configured "policy" of dates and times.

This policy is referred to as the promotion/demotion set and simply consists of the timestamp range a given catalog name should be present in a pkginfo's catalogs key. Once the initial pro/dem set is configured in the pkginfo autopromoter will then manage the lifecycle of which catalogs ought to be in the pkginfo at any given time. The most common use case is to remove some of the monotomy in the workflow of moving a pkginfo from, say, the testing catalog to the production catalog.

## Getting started

To initialize the pro/dem set in a given pkginfo with the default policy simply run autopromoter on a pkginfo file with no other arguments:

```bash
autopromoter.py Firefox-39.0.plist
```

For a pkginfo that has no pro/dem set yet you'll probably see output similar to this:

```
processing pkginfo "Firefox-39.0.plist"...
creating initial promotion/demotion record for catalog development
  promoting on: (now until demotion)
  demoting on:  2015-07-16 20:16:29.231466 (+5 days from now)
creating initial promotion/demotion record for catalog testing
  promoting on: 2015-07-16 20:16:29.231466 (same as prev. cat demotion)
  demoting on:  2015-07-21 20:16:29.231466 (+5 days from prev. cat demotion)
creating initial promotion/demotion record for catalog production
  promoting on: 2015-07-21 20:16:29.231466 (same as prev. cat demotion)
  demoting on: (never after promotion)
catalog development ought to be active now: promoting
catalog testing should not be active now: demoting
writing changed pkginfo
```

As you can see the default policy is to have three catalogs managed: development, testing, and production with a time of five days in each catalog relative to each other between promotions/demotions.

*Keep in mind the timestamps are UTC and not your local time.*

Now with the initial pro/dem having been set you can keep running autopromoter on this same pkginfo and, when the time is right according to the policy, it will update the pkginfo to demote or promote the appropriate catalogs similar to this:

```
processing pkginfo "Firefox-39.0.plist"...
catalog development should not be active now: demoting
catalog testing ought to be active now: promoting
writing changed pkginfo
```

If there's no changes to be made yet becuase, say, not enough time has yet passed to trigger a promotion or demotion:

```
processing pkginfo "Firefox-39.0.plist"...
no catalog promotions or demotions
```

Because autopromoter does not change pkginfo files unless necessary it is expected that it would be run in an automated fashion (say, nightly) so that promotions and demotions can happen automatically. Though this isn't strictly necessary if you'd like it to run in a semi-automated fashion.

## Understanding pro/dem sets (autopromoter policy), promotions, and demotions

Munki administrators are highly encouraged to manage software packages in different catalogs often representing the stages of testing and deployment they've been through.

As an example workflow: a package that's currently being developed & tested by an IT team would be placed in a "development" catalog but no other catalog yet as a full testing and vetting hasn't been completed. As time passes the vetting and testing (by that IT team) has shown no serious flaws and so it's time to push the package out to a limited set of end-users. Thus it is placed in the "testing" catalog. Finally if no problems are found with the testing user group the package is released to all users by being in a "production" catalog.

This all works well but the the problem arises when keeping track of when these different catalogs ought to be enabled and disabled across an entire repository of packages. Autopromoter aims to fix this by automating these promotions/demotions and keeping track, on a per-package basis, what the current status and expected future status of the packages catalog membership is.

As well there is no method of tracking institutional knowledge about outlier packages. For example say some package needs additional testing time from end-users. By simply changing the pro/dem policy in the pkginfo for that one package it is trivial to manage and keep track of such outliers.

Per above the autopromoter pro/dem sets is just a collection of "valid" timestamps that a catalog should be active for. This collection is stored in the pkginfo file under the 'catalog_promotion' key within the '_metadata' top-level key. It's structure is fairly straight forward nothing when each item was created, and the timestamp of it's promotion and/or demotion. If a promotion or demotion is missing then it means that package will not be demoted or promoted; only it's opposite action will be tested against. For example in the default policy the "production" catalog has no demotion date. This is because once it is finally promoted it's not expected to ever be demoted.

When a catalog in the pro/dem set is valid (that is to say that the current date & time is past that catalog's demotion date or before it's promotion date), but not in the catalog then autopromoter enables that catalog in the pkginfo. Likewise if the catalog is not valid then autopromoter disables that catalog in the pkginfo.

Autopromoter will issue a warning for catalogs that are in the pkginfo but not managed in the pro/dem policy set and will continue to include that catalog in the pkginfo even amongst other promotions/demotions.

## Specifing your own initial pro/dem sets

Autopromoter allows the specification of your own pro/dem policy set. It is specified on the command line with the `--catalog` switch:

```bash
autopromoter.py --catalog pluto --catalog mars:25 Firefox-39.0.plist
```

This will override the default policy and create pro/dem catalog sets for pluto (whith the default demotion delta of five days) and for mars with a specified 10 day demotion delta and the same with the saturn catalog:

```
processing pkginfo "Firefox-39.0.plist"...
creating initial promotion/demotion record for catalog pluto
  promoting on: (now until demotion)
  demoting on:  2015-07-16 21:01:47.524423 (+5 days from now)
creating initial promotion/demotion record for catalog mars
  promoting on: 2015-07-16 21:01:47.524423 (same as prev. cat demotion)
  demoting on:  2015-07-26 21:01:47.524423 (+10 days from prev. cat demotion)
creating initial promotion/demotion record for catalog saturn
  promoting on: 2015-07-26 21:01:47.524423 (same as prev. cat demotion)
  demoting on: (never after promotion)
WARNING: additional catalogs found in pkginfo that are not in the
         promotion/demotion set:
           testing
         please remove catalog(s) from pkginfo file if not desired
catalog pluto ought to be active now: promoting
writing changed pkginfo
```

Note that the day time deltas are based on relative timestamps for the given catalog sets. For example in the above command the pluto catalog has no set promotion date because it should start as promoted. It has a demotion time of 5 days (the default) from the current date and time. The mars catalog has a demotion day the same as the previous catalog's promotion date (so that the two catalogs can be demoted and promoted at the same time).

While saturn did specify a 10 day delta it gets no demotion time. The implicit behaviour of managing a list of catalogs is that the beginning catalog is immediately available and the last catalog will never be demoted (because it's the last catalog in the chain). This order is established by the order of catalog arguments specified to autopromoter or the default set of catalogs (development, testing, production).

## Future things

Autopromoter is a very simple (perhaps too simple) tool to manage the autopromotion and demotion of catalogs in an escalating testing-type workflow.

Ideally it would have the ability to manage one's entire Munki repository being somewhat smart about initializations. Right now it can perform it's normal promotion/workflow logic on multiple pkginfos but it's not really suitable nor user freindly to specifiy all pkginfos at this time (it will likely un-production your existing production pkginfos).

As well it would be good to make it far more extensible such that it can have Plist output modes and other automation-freindly features. Perhaps it can be plugged into other catalog management or web UI management tools, etc.

Cheers!
