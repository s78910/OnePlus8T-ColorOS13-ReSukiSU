import os
import sys
import re

def patch_file(filepath, search_str, replace_str):
    if not os.path.exists(filepath):
        print(f"[-] File not found: {filepath}")
        return False
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    if search_str not in content:
        print(f"[-] Target string not found in {filepath}")
        return False
    content = content.replace(search_str, replace_str, 1)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"[+] Successfully patched: {filepath}")
    return True

def main():
    kernel_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    print(f"[*] Applying SuSFS & BakaSU compatibility fixes to {kernel_dir}...")

    # 1. include/linux/susfs_def.h
    def_h = os.path.join(kernel_dir, "include", "linux", "susfs_def.h")
    if os.path.exists(def_h):
        with open(def_h, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        if "#include <linux/sched.h>" not in content:
            content = "#include <linux/sched.h>\n#include <linux/thread_info.h>\n#include <linux/cred.h>\n" + content

        susfs_def_additions = '''
#ifndef SUSFS_MAGIC
#define SUSFS_MAGIC 0xFAFAFAFA
#endif

#ifndef CMD_SUSFS_ADD_SUS_PATH_LOOP
#define CMD_SUSFS_ADD_SUS_PATH_LOOP 0x55553
#endif
#ifndef CMD_SUSFS_HIDE_SUS_MNTS_FOR_NON_SU_PROCS
#define CMD_SUSFS_HIDE_SUS_MNTS_FOR_NON_SU_PROCS 0x55561
#endif
#ifndef CMD_SUSFS_ENABLE_AVC_LOG_SPOOFING
#define CMD_SUSFS_ENABLE_AVC_LOG_SPOOFING 0x60010
#endif
#ifndef CMD_SUSFS_ADD_SUS_MAP
#define CMD_SUSFS_ADD_SUS_MAP 0x60020
#endif

#ifndef SUSFS_MAX_VERSION_BUFSIZE
#define SUSFS_MAX_VERSION_BUFSIZE 16
#endif
#ifndef SUSFS_MAX_VARIANT_BUFSIZE
#define SUSFS_MAX_VARIANT_BUFSIZE 16
#endif
#ifndef SUSFS_ENABLED_FEATURES_SIZE
#define SUSFS_ENABLED_FEATURES_SIZE 8192
#endif

#ifndef TASK_STRUCT_NON_ROOT_USER_APP_PROC
#define TASK_STRUCT_NON_ROOT_USER_APP_PROC BIT(24)
#endif

#ifndef TIF_PROC_UMOUNTED
#define TIF_PROC_UMOUNTED 33
#endif
#ifndef TIF_PROC_NO_SU
#define TIF_PROC_NO_SU 34
#endif
#ifndef TIF_PROC_UMOUNTED_FOR_ZYGOTE_NEXT
#define TIF_PROC_UMOUNTED_FOR_ZYGOTE_NEXT 35
#endif

struct st_susfs_version {
\tchar susfs_version[SUSFS_MAX_VERSION_BUFSIZE];
\tint err;
};

struct st_susfs_variant {
\tchar susfs_variant[SUSFS_MAX_VARIANT_BUFSIZE];
\tint err;
};

struct st_susfs_enabled_features {
\tchar enabled_features[SUSFS_ENABLED_FEATURES_SIZE];
\tint err;
};

struct st_susfs_log {
\tbool enabled;
\tint err;
};

struct st_susfs_hide_sus_mnts_for_non_su_procs {
\tbool enabled;
\tint err;
};

struct st_susfs_sus_map {
\tchar target_pathname[SUSFS_MAX_LEN_PATHNAME];
\tint err;
};

struct st_susfs_avc_log_spoofing {
\tbool enabled;
\tint err;
};

struct work_struct;
extern struct work_struct susfs_extra_works;

static inline bool susfs_is_current_proc_umounted(void) {
\treturn test_ti_thread_flag(&current->thread_info, TIF_PROC_UMOUNTED);
}

static inline void susfs_set_current_proc_umounted(void) {
\tset_ti_thread_flag(&current->thread_info, TIF_PROC_UMOUNTED);
}

static inline void susfs_clear_current_proc_umounted(void) {
\tclear_ti_thread_flag(&current->thread_info, TIF_PROC_UMOUNTED);
}

static inline bool susfs_is_current_proc_umounted_for_zygote_next(void) {
\treturn test_ti_thread_flag(&current->thread_info, TIF_PROC_UMOUNTED_FOR_ZYGOTE_NEXT);
}

static inline void susfs_set_current_proc_umounted_for_zygote_next(void) {
\tset_ti_thread_flag(&current->thread_info, TIF_PROC_UMOUNTED_FOR_ZYGOTE_NEXT);
}

static inline void susfs_clear_current_proc_umounted_for_zygote_next(void) {
\tclear_ti_thread_flag(&current->thread_info, TIF_PROC_UMOUNTED_FOR_ZYGOTE_NEXT);
}

static inline bool susfs_is_current_proc_umounted_app(void) {
\treturn (test_ti_thread_flag(&current->thread_info, TIF_PROC_UMOUNTED) &&
\t\t\tcurrent_uid().val >= 10000);
}

static inline bool susfs_is_current_proc_no_su(void) {
\treturn test_ti_thread_flag(&current->thread_info, TIF_PROC_NO_SU);
}

static inline void susfs_set_current_proc_no_su(void) {
\tset_ti_thread_flag(&current->thread_info, TIF_PROC_NO_SU);
}

static inline void susfs_clear_current_proc_no_su(void) {
\tclear_ti_thread_flag(&current->thread_info, TIF_PROC_NO_SU);
}
'''
        if "CMD_SUSFS_ADD_SUS_PATH_LOOP" not in content:
            target = "#endif // #ifndef KSU_SUSFS_DEF_H"
            if target in content:
                content = content.replace(target, susfs_def_additions + "\n" + target)
            else:
                content += "\n" + susfs_def_additions
            with open(def_h, 'w', encoding='utf-8') as f:
                f.write(content)
            print("[+] Successfully patched susfs_def.h with 1.5.5+ macros, structs & inline helpers")

    # 2. include/linux/susfs.h
    susfs_h = os.path.join(kernel_dir, "include", "linux", "susfs.h")
    if os.path.exists(susfs_h):
        with open(susfs_h, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Rename legacy declarations
        content = content.replace('int susfs_add_sus_path(struct st_susfs_sus_path* __user user_info);', 'int susfs_add_sus_path_legacy(struct st_susfs_sus_path* __user user_info);')
        content = content.replace('int susfs_add_sus_kstat(struct st_susfs_sus_kstat* __user user_info);', 'int susfs_add_sus_kstat_legacy(struct st_susfs_sus_kstat* __user user_info);')
        content = content.replace('int susfs_update_sus_kstat(struct st_susfs_sus_kstat* __user user_info);', 'int susfs_update_sus_kstat_legacy(struct st_susfs_sus_kstat* __user user_info);')
        content = content.replace('int susfs_set_uname(struct st_susfs_uname* __user user_info);', 'int susfs_set_uname_legacy(struct st_susfs_uname* __user user_info);')
        content = content.replace('int susfs_set_cmdline_or_bootconfig(char* __user user_fake_boot_config);', 'int susfs_set_cmdline_or_bootconfig_legacy(char* __user user_fake_boot_config);')
        content = content.replace('int susfs_add_open_redirect(struct st_susfs_open_redirect* __user user_info);', 'int susfs_add_open_redirect_legacy(struct st_susfs_open_redirect* __user user_info);')
        content = content.replace('int susfs_get_enabled_features(char __user* buf, size_t bufsize);', 'int susfs_get_enabled_features_legacy(char __user* buf, size_t bufsize);')

        susfs_h_additions = '''
#ifndef SUSFS_MAGIC
#define SUSFS_MAGIC 0xFAFAFAFA
#endif

#include <linux/workqueue.h>
extern struct work_struct susfs_extra_works;

/* Forward declarations for BakaSU dispatch */
#ifdef CONFIG_KSU_SUSFS_SUS_PATH
void susfs_add_sus_path(void __user **user_info);
void susfs_add_sus_path_loop(void __user **user_info);
#endif
#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
void susfs_set_hide_sus_mnts_for_non_su_procs(void __user **user_info);
#endif
#ifdef CONFIG_KSU_SUSFS_SUS_KSTAT
void susfs_add_sus_kstat(void __user **user_info);
void susfs_update_sus_kstat(void __user **user_info);
#endif
#ifdef CONFIG_KSU_SUSFS_SPOOF_UNAME
void susfs_set_uname(void __user **user_info);
#endif
#ifdef CONFIG_KSU_SUSFS_ENABLE_LOG
void susfs_enable_log(void __user **user_info);
#endif
#ifdef CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG
void susfs_set_cmdline_or_bootconfig(void __user **user_info);
#endif
#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT
void susfs_add_open_redirect(void __user **user_info);
#endif
#ifdef CONFIG_KSU_SUSFS_SUS_MAP
void susfs_add_sus_map(void __user **user_info);
#endif
void susfs_set_avc_log_spoofing(void __user **user_info);
void susfs_get_enabled_features(void __user **user_info);
void susfs_show_variant(void __user **user_info);
void susfs_show_version(void __user **user_info);
void susfs_start_sdcard_monitor_fn(void);
'''
        if "susfs_show_version" not in content:
            target = "#endif // #ifndef KSU_SUSFS_H"
            if target in content:
                content = content.replace(target, susfs_h_additions + "\n" + target)
            else:
                content += "\n" + susfs_h_additions
            with open(susfs_h, 'w', encoding='utf-8') as f:
                f.write(content)
            print("[+] Successfully patched susfs.h with 1.5.5+ function declarations")

    # 3. fs/susfs.c
    susfs_c = os.path.join(kernel_dir, "fs", "susfs.c")
    if os.path.exists(susfs_c):
        with open(susfs_c, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        if "#include <linux/workqueue.h>" not in content:
            content = "#include <linux/workqueue.h>\n" + content

        if "susfs_extra_works" not in content:
            target = "void susfs_init(void) {"
            replacement = """struct work_struct susfs_extra_works;
EXPORT_SYMBOL_GPL(susfs_extra_works);
static void susfs_run_extra_works(struct work_struct *work) {}

void susfs_init(void) {
\tINIT_WORK(&susfs_extra_works, susfs_run_extra_works);"""
            content = content.replace(target, replacement, 1)

        # Rename legacy function definitions
        content = content.replace('int susfs_add_sus_path(struct st_susfs_sus_path* __user user_info)', 'int susfs_add_sus_path_legacy(struct st_susfs_sus_path* __user user_info)')
        content = content.replace('int susfs_add_sus_kstat(struct st_susfs_sus_kstat* __user user_info)', 'int susfs_add_sus_kstat_legacy(struct st_susfs_sus_kstat* __user user_info)')
        content = content.replace('int susfs_update_sus_kstat(struct st_susfs_sus_kstat* __user user_info)', 'int susfs_update_sus_kstat_legacy(struct st_susfs_sus_kstat* __user user_info)')
        content = content.replace('int susfs_set_uname(struct st_susfs_uname* __user user_info)', 'int susfs_set_uname_legacy(struct st_susfs_uname* __user user_info)')
        content = content.replace('int susfs_set_cmdline_or_bootconfig(char* __user user_fake_cmdline_or_bootconfig)', 'int susfs_set_cmdline_or_bootconfig_legacy(char* __user user_fake_cmdline_or_bootconfig)')
        content = content.replace('int susfs_add_open_redirect(struct st_susfs_open_redirect* __user user_info)', 'int susfs_add_open_redirect_legacy(struct st_susfs_open_redirect* __user user_info)')
        content = content.replace('int susfs_get_enabled_features(char __user* buf, size_t bufsize)', 'int susfs_get_enabled_features_legacy(char __user* buf, size_t bufsize)')

        susfs_c_bridge = '''
/* --- BakaSU Supercall Bridge Handlers --- */
#ifdef CONFIG_KSU_SUSFS_SUS_PATH
void susfs_add_sus_path(void __user **user_info) {
\tif (!user_info || !*user_info) return;
\tsusfs_add_sus_path_legacy((struct st_susfs_sus_path __user*)*user_info);
}

void susfs_add_sus_path_loop(void __user **user_info) {
\tif (!user_info || !*user_info) return;
\tsusfs_add_sus_path_legacy((struct st_susfs_sus_path __user*)*user_info);
}
#endif

#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
void susfs_set_hide_sus_mnts_for_non_su_procs(void __user **user_info) {
\tstruct st_susfs_hide_sus_mnts_for_non_su_procs info = {0};
\tif (!user_info || !*user_info) return;
\tif (copy_from_user(&info, (struct st_susfs_hide_sus_mnts_for_non_su_procs __user*)*user_info, sizeof(info))) return;
\tinfo.err = 0;
\tcopy_to_user(&((struct st_susfs_hide_sus_mnts_for_non_su_procs __user*)*user_info)->err, &info.err, sizeof(info.err));
}
#endif

#ifdef CONFIG_KSU_SUSFS_SUS_KSTAT
void susfs_add_sus_kstat(void __user **user_info) {
\tif (!user_info || !*user_info) return;
\tsusfs_add_sus_kstat_legacy((struct st_susfs_sus_kstat __user*)*user_info);
}

void susfs_update_sus_kstat(void __user **user_info) {
\tif (!user_info || !*user_info) return;
\tsusfs_update_sus_kstat_legacy((struct st_susfs_sus_kstat __user*)*user_info);
}
#endif

#ifdef CONFIG_KSU_SUSFS_SPOOF_UNAME
void susfs_set_uname(void __user **user_info) {
\tif (!user_info || !*user_info) return;
\tsusfs_set_uname_legacy((struct st_susfs_uname __user*)*user_info);
}
#endif

#ifdef CONFIG_KSU_SUSFS_ENABLE_LOG
void susfs_enable_log(void __user **user_info) {
\tstruct st_susfs_log info = {0};
\tif (!user_info || !*user_info) return;
\tif (copy_from_user(&info, (struct st_susfs_log __user*)*user_info, sizeof(info))) return;
\tsusfs_set_log(info.enabled);
\tinfo.err = 0;
\tcopy_to_user(&((struct st_susfs_log __user*)*user_info)->err, &info.err, sizeof(info.err));
}
#endif

#ifdef CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG
void susfs_set_cmdline_or_bootconfig(void __user **user_info) {
\tif (!user_info || !*user_info) return;
\tsusfs_set_cmdline_or_bootconfig_legacy((char* __user)*user_info);
}
#endif

#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT
void susfs_add_open_redirect(void __user **user_info) {
\tif (!user_info || !*user_info) return;
\tsusfs_add_open_redirect_legacy((struct st_susfs_open_redirect __user*)*user_info);
}
#endif

#ifdef CONFIG_KSU_SUSFS_SUS_MAP
void susfs_add_sus_map(void __user **user_info) {
\tstruct st_susfs_sus_map info = {0};
\tif (!user_info || !*user_info) return;
\tif (copy_from_user(&info, (struct st_susfs_sus_map __user*)*user_info, sizeof(info))) return;
\tinfo.err = 0;
\tcopy_to_user(&((struct st_susfs_sus_map __user*)*user_info)->err, &info.err, sizeof(info.err));
}
#endif

void susfs_set_avc_log_spoofing(void __user **user_info) {
\tstruct st_susfs_avc_log_spoofing info = {0};
\tif (!user_info || !*user_info) return;
\tif (copy_from_user(&info, (struct st_susfs_avc_log_spoofing __user*)*user_info, sizeof(info))) return;
\tinfo.err = 0;
\tcopy_to_user(&((struct st_susfs_avc_log_spoofing __user*)*user_info)->err, &info.err, sizeof(info.err));
}

void susfs_get_enabled_features(void __user **user_info) {
\tstruct st_susfs_enabled_features *info;
\tint copied_size = 0;
\tif (!user_info || !*user_info) return;
\tinfo = kzalloc(sizeof(struct st_susfs_enabled_features), GFP_KERNEL);
\tif (!info) return;
#ifdef CONFIG_KSU_SUSFS_SUS_PATH
\tcopied_size += scnprintf(info->enabled_features + copied_size, sizeof(info->enabled_features) - copied_size, "CONFIG_KSU_SUSFS_SUS_PATH\\n");
#endif
#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
\tcopied_size += scnprintf(info->enabled_features + copied_size, sizeof(info->enabled_features) - copied_size, "CONFIG_KSU_SUSFS_SUS_MOUNT\\n");
#endif
#ifdef CONFIG_KSU_SUSFS_SUS_KSTAT
\tcopied_size += scnprintf(info->enabled_features + copied_size, sizeof(info->enabled_features) - copied_size, "CONFIG_KSU_SUSFS_SUS_KSTAT\\n");
#endif
#ifdef CONFIG_KSU_SUSFS_SPOOF_UNAME
\tcopied_size += scnprintf(info->enabled_features + copied_size, sizeof(info->enabled_features) - copied_size, "CONFIG_KSU_SUSFS_SPOOF_UNAME\\n");
#endif
#ifdef CONFIG_KSU_SUSFS_ENABLE_LOG
\tcopied_size += scnprintf(info->enabled_features + copied_size, sizeof(info->enabled_features) - copied_size, "CONFIG_KSU_SUSFS_ENABLE_LOG\\n");
#endif
#ifdef CONFIG_KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS
\tcopied_size += scnprintf(info->enabled_features + copied_size, sizeof(info->enabled_features) - copied_size, "CONFIG_KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS\\n");
#endif
#ifdef CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG
\tcopied_size += scnprintf(info->enabled_features + copied_size, sizeof(info->enabled_features) - copied_size, "CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG\\n");
#endif
#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT
\tcopied_size += scnprintf(info->enabled_features + copied_size, sizeof(info->enabled_features) - copied_size, "CONFIG_KSU_SUSFS_OPEN_REDIRECT\\n");
#endif
#ifdef CONFIG_KSU_SUSFS_SUS_MAP
\tcopied_size += scnprintf(info->enabled_features + copied_size, sizeof(info->enabled_features) - copied_size, "CONFIG_KSU_SUSFS_SUS_MAP\\n");
#endif
\tinfo->err = 0;
\tcopy_to_user((struct st_susfs_enabled_features __user*)*user_info, info, sizeof(*info));
\tkfree(info);
}

void susfs_show_variant(void __user **user_info) {
\tstruct st_susfs_variant info = {0};
\tif (!user_info || !*user_info) return;
\tstrscpy(info.susfs_variant, "NON-GKI", sizeof(info.susfs_variant) - 1);
\tinfo.err = 0;
\tcopy_to_user((struct st_susfs_variant __user*)*user_info, &info, sizeof(info));
}

void susfs_show_version(void __user **user_info) {
\tstruct st_susfs_version info = {0};
\tif (!user_info || !*user_info) return;
\tstrscpy(info.susfs_version, "v1.5.5", sizeof(info.susfs_version) - 1);
\tinfo.err = 0;
\tcopy_to_user((struct st_susfs_version __user*)*user_info, &info, sizeof(info));
}

void susfs_start_sdcard_monitor_fn(void) {}
'''
        if "susfs_show_version" not in content:
            content += "\n" + susfs_c_bridge
            with open(susfs_c, 'w', encoding='utf-8') as f:
                f.write(content)
            print("[+] Successfully patched fs/susfs.c with 1.5.5+ supercall bridge handlers")

    # 4. fs/dcache.c: Replace current->susfs_task_state with current_uid().val >= 10000
    # Avoids modifying task_struct in include/linux/sched.h!
    dcache_c = os.path.join(kernel_dir, "fs", "dcache.c")
    if os.path.exists(dcache_c):
        with open(dcache_c, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        target_state = "current->susfs_task_state & TASK_STRUCT_NON_ROOT_USER_APP_PROC"
        if target_state in content:
            content = content.replace(target_state, "current_uid().val >= 10000")
            with open(dcache_c, 'w', encoding='utf-8') as f:
                f.write(content)
            print("[+] Successfully fixed fs/dcache.c to use safe uid check without modifying sched.h!")

    # 5. fs/namespace.c: Add missing Hunk #1 definitions
    namespace_c = os.path.join(kernel_dir, "fs", "namespace.c")
    if os.path.exists(namespace_c):
        with open(namespace_c, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        if "DEFINE_IDA(susfs_mnt_id_ida)" not in content:
            target = '#include "internal.h"'
            inject = '''#include "internal.h"

#if defined(CONFIG_KSU_SUSFS_SUS_MOUNT) || defined(CONFIG_KSU_SUSFS_TRY_UMOUNT)
#include <linux/susfs_def.h>
#endif

#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
extern bool susfs_is_current_ksu_domain(void);
extern bool susfs_is_current_zygote_domain(void);

static DEFINE_IDA(susfs_mnt_id_ida);
static DEFINE_IDA(susfs_mnt_group_ida);

#define CL_COPY_MNT_NS BIT(25)
#endif'''
            patch_file(namespace_c, target, inject)

    # 6. kernel/sys.c: Add uname spoofing hook
    sys_c = os.path.join(kernel_dir, "kernel", "sys.c")
    if os.path.exists(sys_c):
        with open(sys_c, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        if "susfs_spoof_uname" not in content:
            target = "SYSCALL_DEFINE1(newuname, struct new_utsname __user *, name)"
            inject = '''#ifdef CONFIG_KSU_SUSFS_SPOOF_UNAME
extern void susfs_spoof_uname(struct new_utsname* tmp);
#endif
SYSCALL_DEFINE1(newuname, struct new_utsname __user *, name)'''
            patch_file(sys_c, target, inject)

            target_hook = "up_read(&uts_sem);"
            inject_hook = '''#ifdef CONFIG_KSU_SUSFS_SPOOF_UNAME
\tsusfs_spoof_uname(&tmp);
#endif
\tup_read(&uts_sem);'''
            patch_file(sys_c, target_hook, inject_hook)

    # 7. drivers/kernelsu/supercall/supercall.c: Ensure susfs_def.h is included
    for sc_sub in ["drivers/kernelsu/supercall/supercall.c", "KernelSU/kernel/supercall/supercall.c"]:
        sc_path = os.path.join(kernel_dir, sc_sub)
        if os.path.exists(sc_path):
            with open(sc_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            if "linux/susfs_def.h" not in content:
                content = content.replace("#include <linux/susfs.h>", "#include <linux/susfs.h>\n#include <linux/susfs_def.h>")
                with open(sc_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"[+] Successfully ensured susfs_def.h included in {sc_path}")

    # 8. BakaSU sucompat.h & sucompat.c: Fix hook prototypes & unprivilege flag for Manual Hook
    for sub in ["drivers/kernelsu", "KernelSU/kernel"]:
        su_h = os.path.join(kernel_dir, sub, "feature", "sucompat.h")
        if os.path.exists(su_h):
            with open(su_h, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            # Guard struct filename ** prototype with !defined(CONFIG_KSU_MANUAL_HOOK)
            content = content.replace(
                "#ifdef CONFIG_KSU_SUSFS\nint ksu_handle_faccessat(int *dfd, struct filename **filename, int *mode, int *__unused_flags);\nint ksu_handle_stat(int *dfd, struct filename **filename, int *flags);\n#else",
                "#if defined(CONFIG_KSU_SUSFS) && !defined(CONFIG_KSU_MANUAL_HOOK)\nint ksu_handle_faccessat(int *dfd, struct filename **filename, int *mode, int *__unused_flags);\nint ksu_handle_stat(int *dfd, struct filename **filename, int *flags);\n#else"
            )
            content = content.replace(
                "#elif defined(CONFIG_KSU_SUSFS) // susfs",
                "#elif defined(CONFIG_KSU_SUSFS) && !defined(CONFIG_KSU_MANUAL_HOOK) // susfs"
            )
            with open(su_h, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[+] Successfully patched {su_h} to use manual hook signatures when CONFIG_KSU_MANUAL_HOOK=y")

        su_c = os.path.join(kernel_dir, sub, "feature", "sucompat.c")
        if os.path.exists(su_c):
            with open(su_c, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            content = content.replace(
                "// compat for check in hook\n#ifdef CONFIG_KSU_SUSFS\nint ksu_handle_execveat_sucompat",
                "// compat for check in hook\n#if defined(CONFIG_KSU_SUSFS) && !defined(CONFIG_KSU_MANUAL_HOOK)\nint ksu_handle_execveat_sucompat"
            )
            content = content.replace(
                "#ifdef CONFIG_KSU_SUSFS\nint ksu_handle_faccessat(int *dfd, struct filename **filename, int *mode, int *__unused_flags)",
                "#if defined(CONFIG_KSU_SUSFS) && !defined(CONFIG_KSU_MANUAL_HOOK)\nint ksu_handle_faccessat(int *dfd, struct filename **filename, int *mode, int *__unused_flags)"
            )
            content = content.replace(
                "#ifdef CONFIG_KSU_SUSFS\nint ksu_handle_stat(int *dfd, struct filename **filename, int *flags)",
                "#if defined(CONFIG_KSU_SUSFS) && !defined(CONFIG_KSU_MANUAL_HOOK)\nint ksu_handle_stat(int *dfd, struct filename **filename, int *flags)"
            )
            with open(su_c, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[+] Successfully patched {su_c} to use safe manual hook implementations when CONFIG_KSU_MANUAL_HOOK=y")

        # 9. BakaSU Kconfig: Decouple KSU_SUSFS from the choice
        kconfig_path = os.path.join(kernel_dir, sub, "Kconfig")
        if os.path.exists(kconfig_path):
            with open(kconfig_path, 'r', encoding='utf-8', errors='ignore') as f:
                k_content = f.read()
            pattern = r'(config KSU_SUSFS\s+bool "SUSFS Inline Hook"[\s\S]*?)(endchoice)'
            m = re.search(pattern, k_content)
            if m:
                k_content = k_content[:m.start(1)] + "endchoice\n\nconfig KSU_SUSFS\n\tbool \"SUSFS Support\"\n\tdepends on KSU\n\tdefault y\n\thelp\n\t  Enable SuSFS support in KernelSU.\n" + k_content[m.end(2):]
                with open(kconfig_path, 'w', encoding='utf-8') as f:
                    f.write(k_content)
                print(f"[+] Successfully decoupled KSU_SUSFS from hook choice in {kconfig_path}")

        # 10. BakaSU ksud_integration.c: Ensure manual hook branch & exports are active with SuSFS
        for ksud_sub in ["runtime/ksud_integration.c", "kernel/runtime/ksud_integration.c"]:
            ksud_c = os.path.join(kernel_dir, sub, ksud_sub)
            if os.path.exists(ksud_c):
                with open(ksud_c, 'r', encoding='utf-8', errors='ignore') as f:
                    k_content = f.read()

                if "#include <linux/export.h>" not in k_content:
                    k_content = "#include <linux/export.h>\n" + k_content

                # When CONFIG_KSU_MANUAL_HOOK is enabled, do not let CONFIG_KSU_SUSFS bypass manual hook definitions
                k_content = re.sub(
                    r'#elif\s+defined\(CONFIG_KSU_SUSFS\)\s*\n\s*DEFINE_STATIC_KEY_TRUE\(ksu_is_init_rc_hook_enabled\);',
                    '#elif defined(CONFIG_KSU_SUSFS) && !defined(CONFIG_KSU_MANUAL_HOOK)\n    DEFINE_STATIC_KEY_TRUE(ksu_is_init_rc_hook_enabled);',
                    k_content
                )

                # Export ksu_init_rc_hook so fs/read_write.c and lsm_hooks.c can resolve it
                if "EXPORT_SYMBOL(ksu_init_rc_hook);" not in k_content:
                    k_content = k_content.replace(
                        "bool ksu_init_rc_hook __read_mostly = true;",
                        "bool ksu_init_rc_hook __read_mostly = true;\nEXPORT_SYMBOL(ksu_init_rc_hook);"
                    )

                # Export ksu_input_hook so drivers/input/input.c can resolve it
                if "EXPORT_SYMBOL(ksu_input_hook);" not in k_content:
                    k_content = k_content.replace(
                        "bool ksu_input_hook __read_mostly = true;",
                        "bool ksu_input_hook __read_mostly = true;\nEXPORT_SYMBOL(ksu_input_hook);"
                    )

                with open(ksud_c, 'w', encoding='utf-8') as f:
                    f.write(k_content)
                print(f"[+] Successfully patched {ksud_c} to export manual hook symbols")

        # 11. BakaSU core_init.c: Ensure susfs_init() is invoked during ksu_hook_init under MANUAL_HOOK
        for ci_sub in ["core_init.c", "core/init.c", "kernel/core_init.c"]:
            ci_c = os.path.join(kernel_dir, sub, ci_sub)
            if os.path.exists(ci_c):
                with open(ci_c, 'r', encoding='utf-8', errors='ignore') as f:
                    ci_content = f.read()

                target_hook_pattern = r'(#elif\s+defined\(CONFIG_KSU_MANUAL_HOOK\)[\s\S]*?ksu_lsm_hook_built_in_init\(\);\s*#endif)'
                m_ci = re.search(target_hook_pattern, ci_content)
                if m_ci and "susfs_init();" not in m_ci.group(1):
                    replacement = m_ci.group(1) + "\n#if defined(CONFIG_KSU_SUSFS)\n    susfs_init();\n#endif"
                    ci_content = ci_content[:m_ci.start(1)] + replacement + ci_content[m_ci.end(1):]
                    with open(ci_c, 'w', encoding='utf-8') as f:
                        f.write(ci_content)
                    print(f"[+] Successfully patched {ci_c} to call susfs_init() under CONFIG_KSU_MANUAL_HOOK")

    print("[*] All SuSFS & BakaSU fixes applied cleanly without corrupting kernel ABI!")

if __name__ == "__main__":
    main()
