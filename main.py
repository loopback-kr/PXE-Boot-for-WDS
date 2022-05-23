import tarfile, json, requests as req, os, shutil
from os.path import basename, isfile

def extract_in_tar(tar: tarfile.TarFile, file_path: str, dst_path: str=None):
    for member in tar.getmembers():
        if member.path == os.path.sep.join((tar.members[0].path, file_path)):
            if dst_path:
                with open(os.path.sep.join((cfg['remoteinstall_dir'], dst_path)), mode='wb') as f:
                    f.write(tar.extractfile(member).read())
            return tar.extractfile(member).read()
    print('Can\'t find specific file:', file_path)
    return -1


if __name__ == '__main__':
    os.path.sep = '/'

    with open('settings.json') as f:
        cfg = json.load(f)
    
    if not isfile(cfg['archive_file']):
        print('Download syslinux archive...')
        with open(cfg['archive_file'], 'wb') as f:
            download = req.get(os.path.sep.join((cfg['download_url'], cfg['archive_file'])), allow_redirects=True)
            f.write(download.content)
    
    print('Open archive file...')
    tar = tarfile.open(cfg['archive_file'], mode='r:gz')
    
    for arch in cfg['arch'].split('|'):
        print(f'Create {arch} pxelinux files...')
        os.makedirs(f'{cfg["remoteinstall_dir"]}/boot/{arch}/pxelinux.cfg', exist_ok=True)
        extract_in_tar(tar, 'bios/core/pxelinux.0',                     f'boot/{arch}/pxelinux.0')  # Start linux PXE Boot
        extract_in_tar(tar, 'bios/com32/elflink/ldlinux/ldlinux.c32',   f'boot/{arch}/ldlinux.c32') 
        extract_in_tar(tar, 'bios/memdisk/memdisk',                     f'boot/{arch}/memdisk')     # Allow booting legacy operating systems. MEMDISK can boot floppy images, hard disk images and some ISO images.
        extract_in_tar(tar, 'bios/com32/menu/menu.c32',                 f'boot/{arch}/menu.c32')    # Renders a menu on the screen
        extract_in_tar(tar, 'bios/com32/menu/vesamenu.c32',             f'boot/{arch}/vesamenu.c32')# Graphical menu renderer
        extract_in_tar(tar, 'bios/com32/libutil/libutil.c32',           f'boot/{arch}/libutil.c32')
        extract_in_tar(tar, f'efi{"32" if cfg["arch"] == "x86" else "64"}/com32/chain/chain.c32',      f'boot/{arch}/chain.c32')    # Chainload MBRs, partition boot sectors, Windows bootloaders and others...
        extract_in_tar(tar, f'efi{"32" if cfg["arch"] == "x86" else "64"}/com32/modules/reboot.c32',   f'boot/{arch}/reboot.c32')   # Reboot the PC. It supports cold and warn rebooting
        extract_in_tar(tar, f'efi{"32" if cfg["arch"] == "x86" else "64"}/com32/modules/poweroff.c32', f'boot/{arch}/poweroff.c32') # Shutdown the PC
        extract_in_tar(tar, f'efi{"32" if cfg["arch"] == "x86" else "64"}/com32/lib/libcom32.c32',     f'boot/{arch}/libcom32.c32') # 

        # Rename original files
        shutil.copy(f'{cfg["remoteinstall_dir"]}/boot/{arch}/pxeboot.n12',  f'{cfg["remoteinstall_dir"]}/boot/{arch}/pxeboot.0')
        shutil.copy(f'{cfg["remoteinstall_dir"]}/boot/{arch}/abortpxe.com', f'{cfg["remoteinstall_dir"]}/boot/{arch}/abortpxe.0')

        with open(f'{cfg["remoteinstall_dir"]}/Boot/{arch}/pxelinux.cfg/default', 'w') as default:
            default.write(
r'''# Default boot option to use
DEFAULT menu.c32
TIMEOUT 50
# Prompt user for selection
PROMPT 0
# Menu Configuration
MENU WIDTH 80
MENU MARGIN 10
MENU PASSWORDMARGIN 3
MENU ROWS 12
MENU TABMSGROW 18
MENU CMDLINEROW 18
MENU ENDROW 24
MENU PASSWORDROW 11
MENU TIMEOUTROW 20
MENU TITLE PXE Boot Menu

# Menus

# WDS
LABEL WDS
MENU LABEL Windows Deployment Server
KERNEL pxeboot.0'''
            )
#                 default.write(
# r'''DEFAULT vesamenu.c32
# PROMPT 0
# MENU TITLE PXE Boot Menu
# MENU INCLUDE pxelinux.cfg/graphics.conf
# MENU AUTOBOOT Starting Local System in 8 seconds
# # Option 1 - Exit PXE Linux & boot normally
# LABEL bootlocal
# menu label ^Boot Normally
# menu default
# localboot 0
# timeout 80
# TOTALTIMEOUT 9000
# # Option 2 - Run WDS
# LABEL wds
# MENU LABEL ^Windows Deployment Services
# KERNEL pxeboot.0
# # Option 3 - Exit PXE Linux
# LABEL Abort
# MENU LABEL E^xit
# KERNEL abortpxe.0
# # Option 4 - Boot ISO file
# LABEL LABELNAME
# MENU LABEL LABELNAME
# Kernel memdisk
# append iso raw initrd=FILENAME.iso'''
#             )

        with open(f'{cfg["remoteinstall_dir"]}/Boot/{arch}/pxelinux.cfg/graphics.conf', 'w') as default:
            default.write(
r'''MENU MARGIN 10
MENU ROWS 16
MENU TABMSGROW 21
MENU TIMEOUTROW 26
MENU COLOR BORDER 30;44 #00000000 #00000000 none
MENU COLOR SCROLLBAR 30;44 #00000000 #00000000 none
MENU COLOR TITLE 0 #00269B #00000000 none
MENU COLOR SEL 30;47 #40000000 #20ffffff
MENU BACKGROUND background.jpg
NOESCAPE 0
ALLOWOPTIONS 0'''
            )
    tar.close()
    
    # Apply to WDSUtil
    os.system('sc stop WDSServer')
    for arch in cfg['arch'].split('|'):
        os.system(f'wdsutil /set-server /bootprogram:boot\\{"x86" if cfg["fallback_x86"] else arch}\\pxelinux.0 /Architecture:{arch}')
        os.system(f'wdsutil /set-server /N12bootprogram:boot\\{"x86" if cfg["fallback_x86"] else arch}\\pxelinux.0 /Architecture:{arch}')
    os.system('sc start WDSServer')