import os


def clear_dir(top):
    """
    CAREFUL. DANGEROUS
    :param top:
    :return:
    """
    for root, dirs, files in os.walk(top, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))

clear_dir('dist')

import PyInstaller.__main__

PyInstaller.__main__.run([
    'src\\vpnwizard.py',
    '--onefile'
])

os.system('mkdir dist\\data')
os.system('mkdir dist\\install')
os.system('copy src\\data\\* dist\\data\\')
os.system('move dist\\data\\OpenVPN-2.6.4-I001-amd64.msi dist\\install')
os.system('move dist\\data\\stunnel-5.69-win64-installer.exe dist\\install')
os.system('move dist\\data\\stunnel-5.69-android.zip dist\\install')
