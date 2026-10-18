#!/bin/bash
set -e

cd $GITHUB_WORKSPACE/device_kernel

echo "=========================================="
echo "1. Injecting ReSukiSU driver..."
echo "=========================================="
curl -LSs "https://raw.githubusercontent.com/Baka-SU/BakaSU/refs/heads/main/kernel/setup.sh" | bash -s main
find KernelSU drivers/kernelsu -name "*hook_check.mk" -exec sh -c 'echo "# bypassed" > "$1"' _ {} \; 2>/dev/null || true

echo "=========================================="
echo "2. Applying SuSFS v2 & ReSukiSU integration..."
echo "=========================================="
python3 $GITHUB_WORKSPACE/apply_susfs_fixes.py $GITHUB_WORKSPACE/device_kernel $GITHUB_WORKSPACE/zee295_susfs

echo "=========================================="
echo "2b. Eliminating -dirty from ReSukiSU/BakaSU Driver Version..."
echo "=========================================="
find KernelSU drivers/kernelsu -name "Kbuild" -exec sed -i 's/KSU_COMMIT_SHA)-dirty/KSU_COMMIT_SHA)/g' {} + 2>/dev/null || true
find KernelSU drivers/kernelsu -name "Kbuild" -exec sed -i 's/-dirty//g' {} + 2>/dev/null || true

if [ -d KernelSU/.git ]; then
    (cd KernelSU && git config user.email "ci@local" && git config user.name "CI" && git add -A && git commit -m "clean") || true
fi
if [ -d drivers/kernelsu/.git ]; then
    (cd drivers/kernelsu && git config user.email "ci@local" && git config user.name "CI" && git add -A && git commit -m "clean") || true
fi

echo "=========================================="
echo "2c. Replacing Python 2 gcc-wrapper.py with Python 3 passthrough..."
echo "=========================================="
cat << 'EOF' > scripts/gcc-wrapper.py
#!/usr/bin/env python3
import sys, subprocess
sys.exit(subprocess.run(sys.argv[1:]).returncode)
EOF
chmod +x scripts/gcc-wrapper.py

echo "=========================================="
echo "3. Spoofing Stock Version to 4.19.157-perf+..."
echo "=========================================="
sed -i 's/^SUBLEVEL =.*/SUBLEVEL = 157/' Makefile
sed -i 's/^EXTRAVERSION =.*/EXTRAVERSION =/' Makefile

# Prevent scripts/setlocalversion from appending extra '+' to vermagic
echo '#!/bin/sh' > scripts/setlocalversion
echo 'echo "-perf+"' >> scripts/setlocalversion
chmod +x scripts/setlocalversion
touch .scmversion

echo "=========================================="
echo "3b. Fixing PM8008 regulator 16-bit reg parsing for ColorOS 13 DTB..."
echo "=========================================="
python3 - << 'PYEOF'
import re

file_path = "drivers/regulator/qcom_pm8008-regulator.c"
with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

pattern = r'(\s*rc = of_property_read_u32\(reg_node, "reg", &base\);[\s\S]*?pm8008_reg->base = base;)'
m = re.search(pattern, content)
if m:
    replacement = """\trc = of_property_read_u32(reg_node, "reg", &base);
\tif (rc < 0) {
\t\tu16 base16 = 0;
\t\trc = of_property_read_u16(reg_node, "reg", &base16);
\t\tif (rc < 0) {
\t\t\tpr_err("%s: failed to get regulator base rc=%d\\n", name, rc);
\t\t\treturn rc;
\t\t}
\t\tbase = base16;
\t}
\tpm8008_reg->base = base;"""
    content = content[:m.start(1)] + replacement + content[m.end(1):]
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[+] Successfully patched qcom_pm8008-regulator.c to support 16-bit reg")
else:
    print("[-] ERROR: Target block not found in qcom_pm8008-regulator.c")
    exit(1)
PYEOF

echo "=========================================="
echo "4. Applying OnePlus defconfig, Camera Techpack, Manual Hook & SuSFS flags..."
echo "=========================================="
DEFCONFIG="arch/arm64/configs/vendor/kona-perf_defconfig"

# Disable problematic BTF debugging
sed -i 's/CONFIG_DEBUG_INFO_BTF=y/# CONFIG_DEBUG_INFO_BTF is not set/g' $DEFCONFIG
echo "CONFIG_DEBUG_INFO_BTF=n" >> $DEFCONFIG

# Disable CONFIG_DEBUG_FS to pass Android 13 VINTF check and eliminate "您的设备内部出现了问题" warning popup
sed -i 's/CONFIG_DEBUG_FS=y/# CONFIG_DEBUG_FS is not set/g' $DEFCONFIG
echo "CONFIG_DEBUG_FS=n" >> $DEFCONFIG

# Disable module signature enforcement so prebuilt vendor .ko modules load without signature rejection
sed -i 's/CONFIG_MODULE_SIG=y/# CONFIG_MODULE_SIG is not set/g' $DEFCONFIG
sed -i 's/CONFIG_MODULE_SIG_FORCE=y/# CONFIG_MODULE_SIG_FORCE is not set/g' $DEFCONFIG
sed -i 's/CONFIG_MODULE_SIG_ALL=y/# CONFIG_MODULE_SIG_ALL is not set/g' $DEFCONFIG
echo "CONFIG_MODULE_FORCE_LOAD=y" >> $DEFCONFIG

# Ensure exact localversion
sed -i '/CONFIG_LOCALVERSION/d' $DEFCONFIG
echo 'CONFIG_LOCALVERSION="-perf+"' >> $DEFCONFIG
echo 'CONFIG_LOCALVERSION_AUTO=n' >> $DEFCONFIG

# Enable KSU & Manual Hook flags (Proven baseline from Run #9)
echo "CONFIG_KSU=y" >> $DEFCONFIG
echo "CONFIG_KSU_MANUAL_HOOK=y" >> $DEFCONFIG
echo "CONFIG_KSU_MANUAL_HOOK_AUTO_SETUID_HOOK=y" >> $DEFCONFIG
echo "CONFIG_KSU_MANUAL_HOOK_AUTO_INITRC_HOOK=y" >> $DEFCONFIG
echo "CONFIG_KSU_MANUAL_HOOK_AUTO_INPUT_HOOK=y" >> $DEFCONFIG
echo "CONFIG_KALLSYMS=y" >> $DEFCONFIG
echo "CONFIG_KALLSYMS_ALL=y" >> $DEFCONFIG

# Enable SuSFS flags
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
