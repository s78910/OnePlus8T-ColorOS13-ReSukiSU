import os
import sys

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

    # 1. susfs_def.h
    def_h = os.path.join(kernel_dir, "include", "linux", "susfs_def.h")
    if os.path.exists(def_h):
        with open(def_h, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

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

static inline bool susfs_is_current_proc_umounted(void) {
\treturn false;
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
            print(f"[+] Successfully patched susfs_def.h with 1.5.5+ macros & structs")

    # 2. susfs.h
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
            print(f"[+] Successfully patched susfs.h with 1.5.5+ function declarations")

    # 3. fs/susfs.c
    susfs_c = os.path.join(kernel_dir, "fs", "susfs.c")
    if os.path.exists(susfs_c):
        with open(susfs_c, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

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
\tint ret = 0;
\tif (!user_info || !*user_info) return;
\tret = susfs_add_sus_path_legacy((struct st_susfs_sus_path __user*)*user_info);
\tcopy_to_user(&((struct st_susfs_sus_path __user*)*user_info)->err, &ret, sizeof(ret));
}

void susfs_add_sus_path_loop(void __user **user_info) {
\tint ret = 0;
\tif (!user_info || !*user_info) return;
\tret = susfs_add_sus_path_legacy((struct st_susfs_sus_path __user*)*user_info);
\tcopy_to_user(&((struct st_susfs_sus_path __user*)*user_info)->err, &ret, sizeof(ret));
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
\tint ret = 0;
\tif (!user_info || !*user_info) return;
\tret = susfs_add_sus_kstat_legacy((struct st_susfs_sus_kstat __user*)*user_info);
\tcopy_to_user(&((struct st_susfs_sus_kstat __user*)*user_info)->err, &ret, sizeof(ret));
}

void susfs_update_sus_kstat(void __user **user_info) {
\tint ret = 0;
\tif (!user_info || !*user_info) return;
\tret = susfs_update_sus_kstat_legacy((struct st_susfs_sus_kstat __user*)*user_info);
\tcopy_to_user(&((struct st_susfs_sus_kstat __user*)*user_info)->err, &ret, sizeof(ret));
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
\tint ret = 0;
\tif (!user_info || !*user_info) return;
\tret = susfs_add_open_redirect_legacy((struct st_susfs_open_redirect __user*)*user_info);
\tcopy_to_user(&((struct st_susfs_open_redirect __user*)*user_info)->err, &ret, sizeof(ret));
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
            print(f"[+] Successfully patched fs/susfs.c with 1.5.5+ supercall bridge handlers")

    # 4. sched.h
    sched_h = os.path.join(kernel_dir, "include", "linux", "sched.h")
    if os.path.exists(sched_h):
        with open(sched_h, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        if "susfs_task_state" not in content:
            target = "\trandomized_struct_fields_end"
            inject = "#if defined(CONFIG_KSU_SUSFS)\n\tu64 susfs_task_state;\n\tu64 susfs_last_fake_mnt_id;\n#endif\n\trandomized_struct_fields_end"
            patch_file(sched_h, target, inject)

    # 5. namespace.c
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

    # 6. kernel/sys.c
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

    # 7. drivers/input/input.c: Remove incompatible ksu_input_hook
    input_c = os.path.join(kernel_dir, "drivers", "input", "input.c")
    if os.path.exists(input_c):
        with open(input_c, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        if "ksu_input_hook" in content:
            content = content.replace("extern bool ksu_input_hook __read_mostly;\n", "")
            content = content.replace("if (unlikely(ksu_input_hook))\n\t\tksu_handle_input_handle_event(&type, &code, &value);", "ksu_handle_input_handle_event(&type, &code, &value);")
            content = content.replace("if (unlikely(ksu_input_hook))\n\tksu_handle_input_handle_event(&type, &code, &value);", "ksu_handle_input_handle_event(&type, &code, &value);")
            with open(input_c, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[+] Successfully sanitized incompatible ksu_input_hook from: {input_c}")

    # 8. fs/read_write.c: Remove incompatible ksu_init_rc_hook and ksu_vfs_read_hook
    rw_c = os.path.join(kernel_dir, "fs", "read_write.c")
    if os.path.exists(rw_c):
        with open(rw_c, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        if "ksu_init_rc_hook" in content or "ksu_vfs_read_hook" in content:
            content = content.replace("extern bool ksu_init_rc_hook __read_mostly;\n", "")
            content = content.replace("extern bool ksu_vfs_read_hook __read_mostly;\n", "")
            content = content.replace("if (unlikely(ksu_init_rc_hook))\n\t\tksu_handle_sys_read(fd, &buf, &count);", "ksu_handle_sys_read(fd, &buf, &count);")
            content = content.replace("if (unlikely(ksu_init_rc_hook))\n\tksu_handle_sys_read(fd, &buf, &count);", "ksu_handle_sys_read(fd, &buf, &count);")
            content = content.replace("if (unlikely(ksu_vfs_read_hook))\n\t\tksu_handle_sys_read(fd, &buf, &count);", "ksu_handle_sys_read(fd, &buf, &count);")
            content = content.replace("if (unlikely(ksu_vfs_read_hook))\n\tksu_handle_sys_read(fd, &buf, &count);", "ksu_handle_sys_read(fd, &buf, &count);")
            with open(rw_c, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[+] Successfully sanitized incompatible hooks from: {rw_c}")

    # 9. fs/stat.c: Remove incompatible ksu_init_rc_hook if any
    stat_c = os.path.join(kernel_dir, "fs", "stat.c")
    if os.path.exists(stat_c):
        with open(stat_c, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        if "ksu_init_rc_hook" in content:
            content = content.replace("extern bool ksu_init_rc_hook __read_mostly;\n", "")
            content = content.replace("if (unlikely(ksu_init_rc_hook))\n\t\tksu_handle_stat(&dfd, &filename, &flag);", "ksu_handle_stat(&dfd, &filename, &flag);")
            content = content.replace("if (unlikely(ksu_init_rc_hook))\n\tksu_handle_stat(&dfd, &filename, &flag);", "ksu_handle_stat(&dfd, &filename, &flag);")
            with open(stat_c, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[+] Successfully sanitized incompatible hooks from: {stat_c}")

    # 10. fs/exec.c: Remove incompatible ksu_execveat_hook if any
    exec_c = os.path.join(kernel_dir, "fs", "exec.c")
    if os.path.exists(exec_c):
        with open(exec_c, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        if "ksu_execveat_hook" in content:
            content = content.replace("extern bool ksu_execveat_hook __read_mostly;\n", "")
            content = content.replace("if (unlikely(ksu_execveat_hook))\n\t\tksu_handle_execveat(&fd, &filename, &flags);", "ksu_handle_execveat(&fd, &filename, &flags);")
            content = content.replace("if (unlikely(ksu_execveat_hook))\n\tksu_handle_execveat(&fd, &filename, &flags);", "ksu_handle_execveat(&fd, &filename, &flags);")
            with open(exec_c, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[+] Successfully sanitized incompatible hooks from: {exec_c}")

    # 11. drivers/kernelsu/supercall/supercall.c: Ensure susfs_def.h is included
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

    print("[*] All SuSFS & BakaSU fixes applied!")

if __name__ == "__main__":
    main()
