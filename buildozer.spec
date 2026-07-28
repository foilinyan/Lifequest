[app]

title = Life Quest

package.name = lifequest
package.domain = com.foili

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,ttf

version = 0.1.0

requirements = python3==3.12.10,kivy==2.3.1

orientation = portrait
fullscreen = 0

android.permissions =

android.api = 35
android.minapi = 23

android.ndk = 28c
android.ndk_path = /opt/android-sdk/ndk/28.2.13676358
android.sdk_path = /opt/android-sdk

android.accept_sdk_license = True
android.skip_update = False

android.archs = arm64-v8a

android.allow_backup = True

p4a.bootstrap = sdl2
p4a.branch = master


[buildozer]

log_level = 2
warn_on_root = 1
