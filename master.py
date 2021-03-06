#!/usr/bin/python
# -*- coding: utf-8 -*-

# TODO
# Instalar prebuild-deps dentro del cowbuilder [DONE]
# Ejecutar prebuild-script dentro del cowbuilder [DONE]
# Compilar y configurar dentro del cowbuilder [DONE]
# Meter en reprepro los resultados [DONE]
# Esperar a que otro apt-get termine [DONE]
# Eperar si se está actualizando el chroot
# Contenedores docker para los esclavos
# Implementar bazaar, mercurial y dsc como fuentes de paquetes
# Mejorar la creación de paquete fuente
# Mejorar la inteligencia de inclusión en el repo
# Borrar paquetes del git-checkout [DONE]
# Corregit git_revision [DONE]
# Configurar todo por pbuilderrc

from buildbot.status.html import WebStatus
from buildbot.plugins import changes, buildslave, util, schedulers

from buildhelpers.packages import packages
from buildhelpers.factories import maintenance, packaging
from buildhelpers.config import (available_archs, available_distros,
                                 common_passwd, periodic_build_timer,
                                 git_poller_interval)

GitPoller = changes.GitPoller
BuildSlave = buildslave.BuildSlave
Authz = util.Authz
BasicAuth = util.BasicAuth
BuilderConfig = util.BuilderConfig
FixedParameter = util.FixedParameter
ChangeFilter = util.ChangeFilter
Periodic = schedulers.Periodic
SingleBranchScheduler = schedulers.SingleBranchScheduler
ForceScheduler = schedulers.ForceScheduler

slavesdata = {}
slaves = []
change_source = []
schedulers = []
builders = []
status = [WebStatus(authz=Authz(auth=BasicAuth([('luis', 'luis')]),
                                forceBuild='auth', forceAllBuilds=True,
                                cancelPendingBuild=True,
                                stopBuild=True, stopAllBuilds=True),
                    http_port=8080)]

# Dynamic inclusion of slaves

for arch in available_archs:
    for distro in available_distros:
        slavename = 'slave-'+distro+'-'+arch
        slavesdata[slavename] = {'architecture': arch,
                                 'distribution': distro,
                                 'slavename': slavename}

        slaves.append(BuildSlave(slavename, common_passwd,
                                 properties=slavesdata[slavename]))

# Git pollers

for pkg in packages.keys():
    change_source.append(GitPoller(project=pkg,
                                   pollinterval=git_poller_interval,
                                   repourl=packages[pkg]['repository'],
                                   branch=packages[pkg]['branch']))

# Maintenance builders

for slave in slavesdata.keys():

    buildername = 'maintenance_'+slave

    builders.append(BuilderConfig(name=buildername, factory=maintenance,
                                  slavename=slave))

    schedulers.append(Periodic(name='periodic_'+buildername,
                               builderNames=[buildername],
                               periodicBuildTimer=periodic_build_timer))

    schedulers.append(ForceScheduler(name='forced_'+buildername,
                                     builderNames=[buildername]))

# Package builders

for slave in slavesdata.keys():
    for pkg in packages.keys():

        buildername = pkg+'_'+slave

        sb_sched_props = {
            'package': pkg,
            'repository': packages[pkg]['repository'],
            'branch': packages[pkg]['branch'],
            'prebuild-script': packages[pkg]['prebuild-script'],
            'prebuild-deps': packages[pkg]['prebuild-deps']}

        f_sched_props = [
            FixedParameter(name='package', default=pkg),
            FixedParameter(name='repository',
                                default=packages[pkg]['repository']),
            FixedParameter(name='branch',
                                default=packages[pkg]['branch']),
            FixedParameter(name='prebuild-script',
                                default=packages[pkg]['prebuild-script']),
            FixedParameter(name='prebuild-deps',
                                default=packages[pkg]['prebuild-deps'])]

        change_filter = ChangeFilter(project=pkg,
                                     branch=packages[pkg]['branch'])

        builders.append(BuilderConfig(name=buildername, factory=packaging,
                                      slavename=slave))

        schedulers.append(SingleBranchScheduler(
            name='git_'+buildername, treeStableTimer=10,
            change_filter=change_filter, properties=sb_sched_props,
            builderNames=[buildername]))

        schedulers.append(ForceScheduler(
            name='forced_'+buildername, properties=f_sched_props,
            builderNames=[buildername]))


# Configuracion principal del buildbot
BuildmasterConfig = {
    'changeHorizon': 2,
    'buildHorizon': 2,
    'eventHorizon': 2,
    'logHorizon': 2,
    'buildCacheSize': 5,
    'buildbotURL': 'http://localhost:8080/',
    'protocols': {'pb': {'port': 9989}},
    'slaves': slaves,
    'change_source': change_source,
    'schedulers': schedulers,
    'builders': builders,
    'status': status
}
