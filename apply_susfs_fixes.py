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
        if "TASK_STRUCT_NON_ROOT_USER_APP_PROC" not in content:
            target = "#define INODE_STATE_OPEN_REDIRECT BIT(27)"
            inject = "#define INODE_STATE_OPEN_REDIRECT BIT(27)\n#define TASK_STRUCT_NON_ROOT_USER_APP_PROC BIT(24)"
            patch_file(def_h, target, inject)

    # 2. sched.h
    sched_h = os.path.join(kernel_dir, "include", "linux", "sched.h")
    if os.path.exists(sched_h):
        with open(sched_h, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        if "susfs_task_state" not in content:
            target = "\trandomized_struct_fields_end"
            inject = "#if defined(CONFIG_KSU_SUSFS)\n\tu64 susfs_task_state;\n\tu64 susfs_last_fake_mnt_id;\n#endif\n\trandomized_struct_fields_end"
            patch_file(sched_h, target, inject)

    # 3. namespace.c
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

    # 4. kernel/sys.c
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
	susfs_spoof_uname(&tmp);
#endif
	up_read(&uts_sem);'''
            patch_file(sys_c, target_hook, inject_hook)

    # 5. drivers/input/input.c: Remove incompatible ksu_input_hook
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

    # 6. fs/read_write.c: Remove incompatible ksu_init_rc_hook and ksu_vfs_read_hook
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

    # 7. fs/stat.c: Remove incompatible ksu_init_rc_hook if any
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

    # 8. fs/exec.c: Remove incompatible ksu_execveat_hook if any
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

    print("[*] All SuSFS & BakaSU fixes applied!")

if __name__ == "__main__":
    main()
