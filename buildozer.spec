[app]
title = Life Quest
package.name = lifequest
package.domain = com.foili
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,ttf
version = 0.1.0
requirements = python3,kivy==2.3.1
orientation = portrait
fullscreen = 0
android.permissions =
android.api = 35
android.minapi = 23
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True
p4a.bootstrap = sdl2
p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 1
