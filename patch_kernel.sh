#!/bin/bash
set -e

cd $GITHUB_WORKSPACE/device_kernel

echo "=========================================="
echo "1. Cloning susfs4ksu 4.19 patchset..."
echo "=========================================="
git clone --depth=1 -b kernel-4.19 https://github.com/ShirkNeko/susfs4ksu.git susfs_src

echo "Copying SuSFS source files to kernel..."
cp -f susfs_src/kernel_patches/fs/susfs.c fs/
cp -f susfs_src/kernel_patches/fs/sus_su.c fs/ || true
cp -f susfs_src/kernel_patches/include/linux/susfs.h include/linux/
cp -f susfs_src/kernel_patches/include/linux/susfs_def.h include/linux/
cp -f susfs_src/kernel_patches/include/linux/sus_su.h include/linux/ || true

echo "Applying 50_add_susfs_in_kernel-4.19.patch..."
patch -p1 --forward --ignore-whitespace < susfs_src/kernel_patches/50_add_susfs_in_kernel-4.19.patch || true
grep -q "CONFIG_KSU_SUSFS" fs/Makefile || echo "obj-\$(CONFIG_KSU_SUSFS) += susfs.o" >> fs/Makefile

echo "Applying SuSFS compatibility fixes..."
# 1. Fix TASK_STRUCT_NON_ROOT_USER_APP_PROC in include/linux/susfs_def.h
if ! grep -q "TASK_STRUCT_NON_ROOT_USER_APP_PROC" include/linux/susfs_def.h; then
  sed -i '/#define INODE_STATE_OPEN_REDIRECT/a\#define TASK_STRUCT_NON_ROOT_USER_APP_PROC BIT(24)' include/linux/susfs_def.h
fi

# 2. Fix susfs_task_state in include/linux/sched.h
if ! grep -q "susfs_task_state" include/linux/sched.h; then
  sed -i '/randomized_struct_fields_end/i\#if defined(CONFIG_KSU_SUSFS)\n\tu64 susfs_task_state;\n\tu64 susfs_last_fake_mnt_id;\n#endif' include/linux/sched.h
fi

# 3. Fix namespace.c Hunk #1
if ! grep -q "susfs_mnt_id_ida" fs/namespace.c; then
  sed -i '/#include "internal.h"/a\#if defined(CONFIG_KSU_SUSFS_SUS_MOUNT) || defined(CONFIG_KSU_SUSFS_TRY_UMOUNT)\n#include <linux/susfs_def.h>\n#endif\n#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\nextern bool susfs_is_current_ksu_domain(void);\nextern bool susfs_is_current_zygote_domain(void);\nstatic DEFINE_IDA(susfs_mnt_id_ida);\nstatic DEFINE_IDA(susfs_mnt_group_ida);\n#define CL_COPY_MNT_NS BIT(25)\n#endif' fs/namespace.c
fi

echo "=========================================="
echo "2. Injecting ReSukiSU driver..."
echo "=========================================="
curl -LSs "https://raw.githubusercontent.com/Baka-SU/BakaSU/refs/heads/main/kernel/setup.sh" | bash -s main

echo "=========================================="
echo "3. Injecting non-GKI 4.19 syscall hooks..."
echo "=========================================="
curl -LSs "https://raw.githubusercontent.com/JackA1ltman/NonGKI_Kernel_Build_2nd/refs/heads/mainline/Patches/syscall_hook_patches.sh" | bash -s

echo "=========================================="
echo "4. Spoofing Stock Version to 4.19.157-perf+..."
echo "=========================================="
sed -i 's/^SUBLEVEL =.*/SUBLEVEL = 157/' Makefile
sed -i 's/^EXTRAVERSION =.*/EXTRAVERSION =/' Makefile

echo "=========================================="
echo "5. Applying OnePlus defconfig & SuSFS flags..."
echo "=========================================="
DEFCONFIG="arch/arm64/configs/vendor/kona-perf_defconfig"
sed -i '$a\CONFIG_TECHPACK_CAMERA_ONEPLUS=y' $DEFCONFIG
sed -i '/-include oplus_native_features.mk/i\export BRAND_SHOW_FLAG=oneplus' OplusKernelEnvConfig.mk

# Disable problematic BTF debugging
sed -i 's/CONFIG_DEBUG_INFO_BTF=y/# CONFIG_DEBUG_INFO_BTF is not set/g' $DEFCONFIG
echo "CONFIG_DEBUG_INFO_BTF=n" >> $DEFCONFIG

# Ensure exact localversion
sed -i '/CONFIG_LOCALVERSION/d' $DEFCONFIG
echo 'CONFIG_LOCALVERSION="-perf+"' >> $DEFCONFIG
echo 'CONFIG_LOCALVERSION_AUTO=n' >> $DEFCONFIG

# Enable KSU & SuSFS flags
echo "CONFIG_KSU=y" >> $DEFCONFIG
echo "CONFIG_KSU_SUSFS=y" >> $DEFCONFIG
echo "CONFIG_KSU_SUSFS_SUS_PATH=y" >> $DEFCONFIG
echo "CONFIG_KSU_SUSFS_SUS_MOUNT=y" >> $DEFCONFIG
echo "CONFIG_KSU_SUSFS_SUS_KSTAT=y" >> $DEFCONFIG
echo "CONFIG_KSU_SUSFS_SPOOF_UNAME=y" >> $DEFCONFIG
echo "CONFIG_KSU_SUSFS_ENABLE_LOG=y" >> $DEFCONFIG
echo "CONFIG_KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS=y" >> $DEFCONFIG
echo "CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG=y" >> $DEFCONFIG
echo "CONFIG_KSU_SUSFS_OPEN_REDIRECT=y" >> $DEFCONFIG
echo "CONFIG_KSU_SUSFS_SUS_MAP=y" >> $DEFCONFIG

echo "[+] patch_kernel.sh completed successfully!"
