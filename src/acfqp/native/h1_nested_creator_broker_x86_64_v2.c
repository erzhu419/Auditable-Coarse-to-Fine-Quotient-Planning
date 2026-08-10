/*
 * Source-closed Linux x86-64 BROKER role for the bounded H1 creator chain.
 *
 * An external guardian execs this freestanding static image with exactly one
 * AF_UNIX/SOCK_SEQPACKET endpoint on fd 3.  The image authenticates every
 * guardian command with SCM_CREDENTIALS and implements this fixed protocol:
 *
 *   READY(0) -> GO(1) -> GO_ECHO(1)
 *     [-> CREATE_ROLE(2, WORKER) -> PARENT_RETURN(+pidfd)
 *       -> ACK -> ACK_ECHO -> ROLE_REAP]
 *     [-> CREATE_ROLE(3, BUSINESS) -> PARENT_RETURN(+pidfd)
 *       -> ACK -> ACK_ECHO -> ROLE_REAP]
 *   -> SHUTDOWN(4) -> BYE(4).
 *
 * Each CREATE_ROLE command transfers exactly four CLOEXEC descriptors:
 *
 *   0: guardian-supplied cgroup-v2 directory;
 *   1: writable shared 4096-byte PID-cell memfd;
 *   2: fully sealed Linux x86-64 ET_EXEC ELF memfd;
 *   3: guardian-supplied SOCK_SEQPACKET endpoint.
 *
 * The BROKER performs clone3(CLONE_INTO_CGROUP | CLONE_PIDFD), is the real
 * child creator, installs the role channel as child fd 3, and execveat()s the
 * supplied sealed image.  After guardian ACK it blocks until the role exits,
 * performs WNOWAIT plus consuming waitid, proves ECHILD, and reports ROLE_REAP.
 * WORKER and BUSINESS are deliberately sequential; either both may be skipped
 * by SHUTDOWN, and BUSINESS may be skipped after WORKER.  This image does not
 * contain worker/business policy logic or issue any construction authority.
 */

#include <stdint.h>

#define SYS_close 3
#define SYS_fstat 5
#define SYS_lseek 8
#define SYS_mmap 9
#define SYS_munmap 11
#define SYS_rt_sigprocmask 14
#define SYS_pread64 17
#define SYS_getpid 39
#define SYS_kill 62
#define SYS_sendto 44
#define SYS_sendmsg 46
#define SYS_recvmsg 47
#define SYS_getuid 102
#define SYS_getgid 104
#define SYS_getppid 110
#define SYS_fstatfs 138
#define SYS_prctl 157
#define SYS_fcntl 72
#define SYS_getsockopt 55
#define SYS_exit_group 231
#define SYS_waitid 247
#define SYS_dup3 292
#define SYS_execveat 322
#define SYS_pidfd_send_signal 424
#define SYS_clone3 435
#define SYS_close_range 436
#define SYS_setsockopt 54

#define SOL_SOCKET 1
#define SCM_RIGHTS 1
#define SCM_CREDENTIALS 2
#define SO_TYPE 3
#define SO_PASSCRED 16
#define SO_PEERCRED 17
#define SOCK_SEQPACKET 5
#define MSG_TRUNC 0x20
#define MSG_CTRUNC 0x08
#define MSG_NOSIGNAL 0x4000
#define MSG_CMSG_CLOEXEC 0x40000000
#define MSG_EOR 0x80

#define PROT_READ 1
#define PROT_WRITE 2
#define MAP_SHARED 1
#define MAP_FAILED ((void *)(intptr_t)-1)

#define PR_SET_PDEATHSIG 1
#define SIGKILL 9
#define SIGCHLD 17
#define SIG_SETMASK 2

#define P_PID 1
#define P_PIDFD 3
#define WNOHANG 1
#define WEXITED 4
#define WNOWAIT 0x01000000
#define ECHILD 10

#define CLONE_PIDFD 0x00001000ULL
#define CLONE_PARENT_SETTID 0x00100000ULL
#define CLONE_CLEAR_SIGHAND 0x100000000ULL
#define CLONE_INTO_CGROUP 0x200000000ULL

#define AT_EMPTY_PATH 0x1000
#define O_CLOEXEC 02000000
#define F_GETFD 1
#define FD_CLOEXEC 1
#define F_GET_SEALS 1034
#define REQUIRED_ELF_SEALS 15
#define REQUIRED_PID_CELL_PRE_SEALS 6
#define ESRCH 3
#define CGROUP2_SUPER_MAGIC 0x63677270
#define S_IFMT 0170000
#define S_IFDIR 0040000
#define S_IFREG 0100000

#define CONTROL_FD 3
#define CHILD_EXEC_FD 4
#define MAX_CONTROL_BYTES 160
#define FRAME_BYTES 64
#define PID_CELL_BYTES 4096

#define FRAME_MAGIC 0x3256524243514641ULL /* "AFQCBRV2", little endian */
#define FRAME_VERSION 2U

enum opcode_v2 {
    OP_BROKER_READY = 1,
    OP_BROKER_GO = 2,
    OP_BROKER_GO_ECHO = 3,
    OP_CREATE_ROLE = 4,
    OP_ROLE_PARENT_RETURN = 5,
    OP_ROLE_ACK = 6,
    OP_ROLE_ACK_ECHO = 7,
    OP_ROLE_REAP = 8,
    OP_BROKER_SHUTDOWN = 9,
    OP_BROKER_BYE = 10,
    OP_PROTOCOL_FAILURE = 11,
};

enum role_slot_v2 {
    ROLE_WORKER = 1,
    ROLE_BUSINESS = 2,
};

struct frame_v2 {
    uint64_t magic;
    uint32_t version;
    uint32_t opcode;
    uint64_t sequence;
    uint8_t nonce[16];
    int64_t pid;
    int32_t status;
    uint32_t flags;
    uint64_t fact_a;
};

struct iovec_v2 {
    void *base;
    uint64_t length;
};

struct msghdr_v2 {
    void *name;
    uint32_t namelen;
    uint32_t pad0;
    struct iovec_v2 *iov;
    uint64_t iovlen;
    void *control;
    uint64_t controllen;
    uint32_t flags;
    uint32_t pad1;
};

struct cmsghdr_v2 {
    uint64_t length;
    int32_t level;
    int32_t type;
};

struct ucred_v2 {
    int32_t pid;
    uint32_t uid;
    uint32_t gid;
};

/* Linux x86-64 stat ABI. */
struct stat_v2 {
    uint64_t device;
    uint64_t inode;
    uint64_t links;
    uint32_t mode;
    uint32_t uid;
    uint32_t gid;
    uint32_t pad0;
    uint64_t rdevice;
    int64_t size;
    int64_t block_size;
    int64_t blocks;
    int64_t atime_seconds;
    int64_t atime_nanoseconds;
    int64_t mtime_seconds;
    int64_t mtime_nanoseconds;
    int64_t ctime_seconds;
    int64_t ctime_nanoseconds;
    int64_t unused[3];
};

struct statfs_v2 {
    int64_t type;
    int64_t block_size;
    uint64_t blocks;
    uint64_t blocks_free;
    uint64_t blocks_available;
    uint64_t files;
    uint64_t files_free;
    uint64_t fsid[2];
    int64_t name_length;
    int64_t fragment_size;
    int64_t flags;
    int64_t spare[4];
};

struct clone_args_v2 {
    uint64_t flags;
    uint64_t pidfd;
    uint64_t child_tid;
    uint64_t parent_tid;
    uint64_t exit_signal;
    uint64_t stack;
    uint64_t stack_size;
    uint64_t tls;
    uint64_t set_tid;
    uint64_t set_tid_size;
    uint64_t cgroup;
};

struct siginfo_v2 {
    int32_t signo;
    int32_t error;
    int32_t code;
    int32_t pad0;
    int32_t pid;
    uint32_t uid;
    int32_t status;
    uint8_t tail[100];
};

struct received_v2 {
    struct frame_v2 frame;
    int32_t fds[4];
    uint32_t fd_count;
    struct ucred_v2 credential;
    uint32_t credential_count;
};

_Static_assert(sizeof(struct frame_v2) == FRAME_BYTES,
               "BROKER V2 frame ABI changed");
_Static_assert(sizeof(struct ucred_v2) == 12,
               "Linux SCM_CREDENTIALS ABI changed");
_Static_assert(sizeof(struct clone_args_v2) == 88,
               "Linux clone3 ABI changed");
_Static_assert(sizeof(struct siginfo_v2) == 128,
               "Linux waitid siginfo ABI changed");
_Static_assert(sizeof(struct stat_v2) == 144,
               "Linux x86-64 stat ABI changed");

static inline long syscall6(long number, long a1, long a2, long a3, long a4,
                            long a5, long a6) {
    register long r10 __asm__("r10") = a4;
    register long r8 __asm__("r8") = a5;
    register long r9 __asm__("r9") = a6;
    long result;
    __asm__ volatile("syscall"
                     : "=a"(result)
                     : "a"(number), "D"(a1), "S"(a2), "d"(a3), "r"(r10),
                       "r"(r8), "r"(r9)
                     : "rcx", "r11", "memory");
    return result;
}

static inline long syscall5(long n, long a1, long a2, long a3, long a4,
                            long a5) {
    return syscall6(n, a1, a2, a3, a4, a5, 0);
}

static inline long syscall4(long n, long a1, long a2, long a3, long a4) {
    return syscall6(n, a1, a2, a3, a4, 0, 0);
}

static inline long syscall3(long n, long a1, long a2, long a3) {
    return syscall6(n, a1, a2, a3, 0, 0, 0);
}

static inline long syscall2(long n, long a1, long a2) {
    return syscall6(n, a1, a2, 0, 0, 0, 0);
}

static inline long syscall1(long n, long a1) {
    return syscall6(n, a1, 0, 0, 0, 0, 0);
}

static inline long syscall0(long n) {
    return syscall6(n, 0, 0, 0, 0, 0, 0);
}

static void zero_bytes(void *target, uint64_t count) {
    uint8_t *out = (uint8_t *)target;
    uint64_t index;
    for (index = 0; index < count; ++index)
        out[index] = 0;
}

static void copy_bytes(void *target, const void *source, uint64_t count) {
    uint8_t *out = (uint8_t *)target;
    const uint8_t *in = (const uint8_t *)source;
    uint64_t index;
    for (index = 0; index < count; ++index)
        out[index] = in[index];
}

static int equal_bytes(const void *left, const void *right, uint64_t count) {
    const uint8_t *a = (const uint8_t *)left;
    const uint8_t *b = (const uint8_t *)right;
    uint64_t index;
    uint8_t difference = 0;
    for (index = 0; index < count; ++index)
        difference |= (uint8_t)(a[index] ^ b[index]);
    return difference == 0;
}

static int all_zero_bytes(const void *source, uint64_t count) {
    const uint8_t *in = (const uint8_t *)source;
    uint64_t index;
    uint8_t observed = 0;
    for (index = 0; index < count; ++index)
        observed |= in[index];
    return observed == 0;
}

static uint64_t aligned_cmsg(uint64_t value) {
    return (value + 7U) & ~7ULL;
}

static int valid_frame(const struct frame_v2 *frame, uint32_t opcode,
                       uint64_t sequence) {
    return frame->magic == FRAME_MAGIC && frame->version == FRAME_VERSION &&
           frame->opcode == opcode && frame->sequence == sequence;
}

static void initialize_frame(struct frame_v2 *frame, uint32_t opcode,
                             uint64_t sequence, const uint8_t *nonce) {
    zero_bytes(frame, sizeof(*frame));
    frame->magic = FRAME_MAGIC;
    frame->version = FRAME_VERSION;
    frame->opcode = opcode;
    frame->sequence = sequence;
    if (nonce != (const uint8_t *)0)
        copy_bytes(frame->nonce, nonce, sizeof(frame->nonce));
}

static long send_plain(int descriptor, const struct frame_v2 *frame) {
    return syscall6(SYS_sendto, descriptor, (long)frame, sizeof(*frame),
                    MSG_NOSIGNAL, 0, 0);
}

static long send_pidfd(int descriptor, const struct frame_v2 *frame,
                       int pidfd) {
    struct iovec_v2 iov;
    struct msghdr_v2 message;
    uint8_t control[24];
    struct cmsghdr_v2 *header;
    zero_bytes(&message, sizeof(message));
    zero_bytes(control, sizeof(control));
    iov.base = (void *)frame;
    iov.length = sizeof(*frame);
    message.iov = &iov;
    message.iovlen = 1;
    message.control = control;
    message.controllen = sizeof(control);
    header = (struct cmsghdr_v2 *)control;
    header->length = 20;
    header->level = SOL_SOCKET;
    header->type = SCM_RIGHTS;
    copy_bytes(control + 16, &pidfd, sizeof(pidfd));
    return syscall3(SYS_sendmsg, descriptor, (long)&message, MSG_NOSIGNAL);
}

static void close_received(struct received_v2 *received) {
    uint32_t index;
    for (index = 0; index < received->fd_count && index < 4; ++index) {
        if (received->fds[index] >= 0)
            (void)syscall1(SYS_close, received->fds[index]);
        received->fds[index] = -1;
    }
    received->fd_count = 0;
}

static int discard_control_rights(struct received_v2 *received,
                                  uint8_t *control,
                                  uint64_t control_bytes,
                                  int error) {
    uint64_t offset = 0;
    while (offset + sizeof(struct cmsghdr_v2) <= control_bytes) {
        struct cmsghdr_v2 *header =
            (struct cmsghdr_v2 *)(control + offset);
        uint64_t data_bytes;
        uint64_t index;
        if (header->length < sizeof(*header) ||
            header->length > control_bytes - offset)
            break;
        data_bytes = header->length - sizeof(*header);
        if (header->level == SOL_SOCKET && header->type == SCM_RIGHTS &&
            data_bytes % sizeof(int32_t) == 0) {
            for (index = 0; index < data_bytes / sizeof(int32_t); ++index) {
                int32_t descriptor;
                copy_bytes(&descriptor,
                           control + offset + sizeof(*header) +
                               index * sizeof(int32_t),
                           sizeof(descriptor));
                if (descriptor >= 0)
                    (void)syscall1(SYS_close, descriptor);
            }
        }
        offset += aligned_cmsg(header->length);
    }
    received->fd_count = 0;
    return error;
}

static int receive_frame(int descriptor, struct received_v2 *received,
                         int32_t expected_pid, uint32_t expected_uid,
                         uint32_t expected_gid) {
    struct iovec_v2 iov;
    struct msghdr_v2 message;
    uint8_t payload[FRAME_BYTES + 1];
    uint8_t control[MAX_CONTROL_BYTES];
    uint64_t offset;
    long count;
    uint32_t index;
    zero_bytes(received, sizeof(*received));
    for (index = 0; index < 4; ++index)
        received->fds[index] = -1;
    zero_bytes(&message, sizeof(message));
    zero_bytes(payload, sizeof(payload));
    zero_bytes(control, sizeof(control));
    iov.base = payload;
    iov.length = sizeof(payload);
    message.iov = &iov;
    message.iovlen = 1;
    message.control = control;
    message.controllen = sizeof(control);
    count = syscall3(SYS_recvmsg, descriptor, (long)&message,
                     MSG_CMSG_CLOEXEC);
    if (count != FRAME_BYTES || message.namelen != 0 ||
        (message.flags & (MSG_TRUNC | MSG_CTRUNC)) != 0 ||
        (message.flags & ~(MSG_CMSG_CLOEXEC | MSG_EOR)) != 0)
        return discard_control_rights(received, control,
                                      message.controllen, -1);
    copy_bytes(&received->frame, payload, FRAME_BYTES);
    offset = 0;
    while (offset + sizeof(struct cmsghdr_v2) <= message.controllen) {
        struct cmsghdr_v2 *header =
            (struct cmsghdr_v2 *)(control + offset);
        uint64_t data_bytes;
        if (header->length < sizeof(*header) ||
            header->length > message.controllen - offset)
            return discard_control_rights(received, control,
                                          message.controllen, -2);
        data_bytes = header->length - sizeof(*header);
        if (header->level != SOL_SOCKET)
            return discard_control_rights(received, control,
                                          message.controllen, -3);
        if (header->type == SCM_CREDENTIALS) {
            if (data_bytes != sizeof(struct ucred_v2) ||
                received->credential_count != 0)
                return discard_control_rights(received, control,
                                              message.controllen, -4);
            copy_bytes(&received->credential, control + offset + 16,
                       sizeof(received->credential));
            received->credential_count = 1;
        } else if (header->type == SCM_RIGHTS) {
            if (data_bytes == 0 || data_bytes % sizeof(int32_t) != 0 ||
                received->fd_count != 0 || data_bytes / sizeof(int32_t) > 4)
                return discard_control_rights(received, control,
                                              message.controllen, -5);
            received->fd_count = (uint32_t)(data_bytes / sizeof(int32_t));
            copy_bytes(received->fds, control + offset + 16, data_bytes);
        } else {
            return discard_control_rights(received, control,
                                          message.controllen, -6);
        }
        offset += aligned_cmsg(header->length);
    }
    if (offset != aligned_cmsg(message.controllen) &&
        offset != message.controllen)
        return discard_control_rights(received, control,
                                      message.controllen, -7);
    if (received->credential_count != 1 ||
        received->credential.pid != expected_pid ||
        received->credential.uid != expected_uid ||
        received->credential.gid != expected_gid)
        return discard_control_rights(received, control,
                                      message.controllen, -8);
    for (index = 0; index < received->fd_count; ++index) {
        if (syscall2(SYS_fcntl, received->fds[index], F_GETFD) != FD_CLOEXEC)
            return discard_control_rights(received, control,
                                          message.controllen, -9);
    }
    return 0;
}

static void protocol_failure(int status, uint64_t sequence,
                             const uint8_t *nonce) {
    struct frame_v2 frame;
    initialize_frame(&frame, OP_PROTOCOL_FAILURE, sequence, nonce);
    frame.pid = syscall0(SYS_getpid);
    frame.status = status;
    (void)send_plain(CONTROL_FD, &frame);
    syscall1(SYS_exit_group, 100 + ((status < 0 ? -status : status) % 20));
    __builtin_unreachable();
}

static void child_exit(int status) {
    syscall1(SYS_exit_group, status);
    __builtin_unreachable();
}

static long wait_known_child(int pidfd, int32_t child_pid,
                             struct siginfo_v2 *information, int options) {
    long result;
    if (pidfd >= 0) {
        result = syscall5(SYS_waitid, P_PIDFD, pidfd, (long)information,
                          options, 0);
        if (result == 0 || result == -ECHILD)
            return result;
        zero_bytes(information, sizeof(*information));
    }
    return syscall5(SYS_waitid, P_PID, child_pid, (long)information,
                    options, 0);
}

static int kill_and_reap(int pidfd, int32_t child_pid) {
    struct siginfo_v2 observed;
    struct siginfo_v2 consumed;
    struct siginfo_v2 empty;
    long result;
    if (child_pid <= 0)
        return -1;
    if (pidfd >= 0)
        result = syscall4(SYS_pidfd_send_signal, pidfd, SIGKILL, 0, 0);
    else
        result = -1;
    if (result != 0 && result != -ESRCH) {
        result = syscall2(SYS_kill, child_pid, SIGKILL);
        if (result != 0 && result != -ESRCH) {
            if (pidfd >= 0)
                (void)syscall1(SYS_close, pidfd);
            return -2;
        }
    }
    zero_bytes(&observed, sizeof(observed));
    result = wait_known_child(pidfd, child_pid, &observed,
                              WEXITED | WNOWAIT);
    if (result == -ECHILD) {
        if (pidfd >= 0)
            (void)syscall1(SYS_close, pidfd);
        return 0;
    }
    if (result != 0 || observed.pid != child_pid) {
        if (pidfd >= 0)
            (void)syscall1(SYS_close, pidfd);
        return -3;
    }
    zero_bytes(&consumed, sizeof(consumed));
    result = wait_known_child(pidfd, child_pid, &consumed, WEXITED);
    if (result != 0 || consumed.pid != child_pid ||
        consumed.status != observed.status || consumed.code != observed.code) {
        if (pidfd >= 0)
            (void)syscall1(SYS_close, pidfd);
        return -4;
    }
    zero_bytes(&empty, sizeof(empty));
    result = wait_known_child(pidfd, child_pid, &empty,
                              WEXITED | WNOHANG);
    if (result != -ECHILD) {
        if (pidfd >= 0)
            (void)syscall1(SYS_close, pidfd);
        return -5;
    }
    if (pidfd >= 0)
        (void)syscall1(SYS_close, pidfd);
    return 0;
}

static void exec_role_child(struct received_v2 *command, void *pid_mapping,
                            int32_t expected_parent_pid) {
    char executable_name[] = "acfqp-broker-created-role-v2";
    char *argv[2];
    char *envp[1];
    int cgroup_fd = command->fds[0];
    int pid_cell_fd = command->fds[1];
    int executable_fd = command->fds[2];
    int child_control_fd = command->fds[3];
    long result;

    result = syscall5(SYS_prctl, PR_SET_PDEATHSIG, SIGKILL, 0, 0, 0);
    if (result < 0 || syscall0(SYS_getppid) != expected_parent_pid)
        child_exit(120);
    if (syscall2(SYS_munmap, (long)pid_mapping, PID_CELL_BYTES) < 0)
        child_exit(121);
    (void)syscall1(SYS_close, pid_cell_fd);
    (void)syscall1(SYS_close, cgroup_fd);
    if (child_control_fd != CONTROL_FD &&
        syscall3(SYS_dup3, child_control_fd, CONTROL_FD, 0) < 0)
        child_exit(122);
    if (executable_fd != CHILD_EXEC_FD &&
        syscall3(SYS_dup3, executable_fd, CHILD_EXEC_FD, O_CLOEXEC) < 0)
        child_exit(123);
    if (syscall3(SYS_close_range, 5, 0xffffffffU, 0) < 0)
        child_exit(124);
    argv[0] = executable_name;
    argv[1] = (char *)0;
    envp[0] = (char *)0;
    (void)syscall5(SYS_execveat, CHILD_EXEC_FD, (long)"", (long)argv,
                   (long)envp, AT_EMPTY_PATH);
    child_exit(126);
}

static int validate_create_rights(const struct received_v2 *command,
                                  int32_t guardian_pid,
                                  uint32_t guardian_uid,
                                  uint32_t guardian_gid) {
    uint8_t elf_identity[20];
    uint8_t pid_cell_bytes[PID_CELL_BYTES + 1];
    struct stat_v2 cgroup_status;
    struct stat_v2 executable_status;
    struct stat_v2 broker_control_status;
    struct stat_v2 child_control_status;
    struct statfs_v2 cgroup_filesystem;
    struct ucred_v2 child_peer;
    uint32_t child_peer_bytes = sizeof(child_peer);
    int socket_type = 0;
    uint32_t socket_type_bytes = sizeof(socket_type);
    if (command->fd_count != 4)
        return -30;
    zero_bytes(&cgroup_status, sizeof(cgroup_status));
    zero_bytes(&cgroup_filesystem, sizeof(cgroup_filesystem));
    if (syscall2(SYS_fstat, command->fds[0], (long)&cgroup_status) != 0 ||
        (cgroup_status.mode & S_IFMT) != S_IFDIR ||
        syscall2(SYS_fstatfs, command->fds[0],
                 (long)&cgroup_filesystem) != 0 ||
        cgroup_filesystem.type != CGROUP2_SUPER_MAGIC)
        return -31;
    zero_bytes(pid_cell_bytes, sizeof(pid_cell_bytes));
    if (syscall4(SYS_pread64, command->fds[1], (long)pid_cell_bytes,
                 sizeof(pid_cell_bytes), 0) != PID_CELL_BYTES ||
        !all_zero_bytes(pid_cell_bytes, PID_CELL_BYTES) ||
        syscall2(SYS_fcntl, command->fds[1], F_GET_SEALS) !=
            REQUIRED_PID_CELL_PRE_SEALS)
        return -32;
    zero_bytes(&executable_status, sizeof(executable_status));
    if (syscall2(SYS_fstat, command->fds[2],
                 (long)&executable_status) != 0 ||
        (executable_status.mode & S_IFMT) != S_IFREG ||
        executable_status.size < 64 ||
        syscall2(SYS_fcntl, command->fds[2], F_GET_SEALS) !=
        REQUIRED_ELF_SEALS)
        return -33;
    zero_bytes(elf_identity, sizeof(elf_identity));
    if (syscall4(SYS_pread64, command->fds[2], (long)elf_identity,
                 sizeof(elf_identity), 0) != sizeof(elf_identity) ||
        elf_identity[0] != 0x7f || elf_identity[1] != 'E' ||
        elf_identity[2] != 'L' || elf_identity[3] != 'F' ||
        elf_identity[4] != 2 || elf_identity[5] != 1 ||
        elf_identity[6] != 1 || elf_identity[16] != 2 ||
        elf_identity[17] != 0 || elf_identity[18] != 0x3e ||
        elf_identity[19] != 0)
        return -34;
    if (syscall5(SYS_getsockopt, command->fds[3], SOL_SOCKET, SO_TYPE,
                 (long)&socket_type, (long)&socket_type_bytes) != 0 ||
        socket_type_bytes != sizeof(socket_type) ||
        socket_type != SOCK_SEQPACKET)
        return -35;
    zero_bytes(&child_peer, sizeof(child_peer));
    if (syscall5(SYS_getsockopt, command->fds[3], SOL_SOCKET, SO_PEERCRED,
                 (long)&child_peer, (long)&child_peer_bytes) != 0 ||
        child_peer_bytes != sizeof(child_peer) ||
        child_peer.pid != guardian_pid || child_peer.uid != guardian_uid ||
        child_peer.gid != guardian_gid)
        return -36;
    zero_bytes(&broker_control_status, sizeof(broker_control_status));
    zero_bytes(&child_control_status, sizeof(child_control_status));
    if (syscall2(SYS_fstat, CONTROL_FD,
                 (long)&broker_control_status) != 0 ||
        syscall2(SYS_fstat, command->fds[3],
                 (long)&child_control_status) != 0 ||
        (broker_control_status.device == child_control_status.device &&
         broker_control_status.inode == child_control_status.inode))
        return -37;
    return 0;
}

static int create_and_reap_role(struct received_v2 *command,
                                int32_t guardian_pid, uint32_t guardian_uid,
                                uint32_t guardian_gid, int32_t self_pid,
                                uint32_t role_slot, uint64_t sequence) {
    struct clone_args_v2 clone_args;
    struct siginfo_v2 observed;
    struct siginfo_v2 consumed;
    struct siginfo_v2 empty;
    struct frame_v2 frame;
    struct received_v2 ack;
    void *pid_mapping;
    int pidfd = -1;
    int32_t child_pid;
    long result;
    int validation;

    validation = validate_create_rights(command, guardian_pid, guardian_uid,
                                        guardian_gid);
    if (validation != 0) {
        close_received(command);
        protocol_failure(validation, sequence, command->frame.nonce);
    }
    pid_mapping = (void *)syscall6(SYS_mmap, 0, PID_CELL_BYTES,
                                   PROT_READ | PROT_WRITE, MAP_SHARED,
                                   command->fds[1], 0);
    if (pid_mapping == MAP_FAILED || (intptr_t)pid_mapping < 0 ||
        !all_zero_bytes(pid_mapping, PID_CELL_BYTES)) {
        close_received(command);
        protocol_failure(-42, sequence, command->frame.nonce);
    }
    zero_bytes(&clone_args, sizeof(clone_args));
    clone_args.flags = CLONE_PIDFD | CLONE_PARENT_SETTID |
                       CLONE_CLEAR_SIGHAND | CLONE_INTO_CGROUP;
    clone_args.pidfd = (uint64_t)(uintptr_t)&pidfd;
    clone_args.parent_tid = (uint64_t)(uintptr_t)pid_mapping;
    clone_args.exit_signal = SIGCHLD;
    clone_args.cgroup = (uint64_t)(uint32_t)command->fds[0];
    result = syscall2(SYS_clone3, (long)&clone_args, sizeof(clone_args));
    if (result == 0)
        exec_role_child(command, pid_mapping, self_pid);
    child_pid = (int32_t)result;
    if (result > 0 &&
        (*(volatile int32_t *)pid_mapping != child_pid ||
         !all_zero_bytes((const uint8_t *)pid_mapping + sizeof(int32_t),
                         PID_CELL_BYTES - sizeof(int32_t)))) {
        (void)syscall2(SYS_munmap, (long)pid_mapping, PID_CELL_BYTES);
        close_received(command);
        if (kill_and_reap(pidfd, child_pid) != 0)
            protocol_failure(-43, sequence, command->frame.nonce);
        protocol_failure(-44, sequence, command->frame.nonce);
    }
    (void)syscall2(SYS_munmap, (long)pid_mapping, PID_CELL_BYTES);
    close_received(command);
    if (result > 0 && pidfd < 0) {
        if (kill_and_reap(pidfd, child_pid) != 0)
            protocol_failure(-57, sequence, command->frame.nonce);
        protocol_failure(-58, sequence, command->frame.nonce);
    }
    if (result <= 0)
        protocol_failure((int)result, sequence, command->frame.nonce);

    initialize_frame(&frame, OP_ROLE_PARENT_RETURN, sequence,
                     command->frame.nonce);
    frame.pid = child_pid;
    frame.flags = role_slot;
    frame.fact_a = (uint64_t)(uint32_t)self_pid;
    if (send_pidfd(CONTROL_FD, &frame, pidfd) != FRAME_BYTES) {
        if (kill_and_reap(pidfd, child_pid) != 0)
            protocol_failure(-45, sequence, command->frame.nonce);
        protocol_failure(-46, sequence, command->frame.nonce);
    }
    result = receive_frame(CONTROL_FD, &ack, guardian_pid, guardian_uid,
                           guardian_gid);
    if (result != 0 || ack.fd_count != 0 ||
        !valid_frame(&ack.frame, OP_ROLE_ACK, sequence) ||
        !equal_bytes(ack.frame.nonce, command->frame.nonce, 16) ||
        ack.frame.pid != child_pid || ack.frame.status != 0 ||
        ack.frame.flags != role_slot || ack.frame.fact_a != 0) {
        close_received(&ack);
        if (kill_and_reap(pidfd, child_pid) != 0)
            protocol_failure(-47, sequence, command->frame.nonce);
        protocol_failure(-48, sequence, command->frame.nonce);
    }
    initialize_frame(&frame, OP_ROLE_ACK_ECHO, sequence,
                     command->frame.nonce);
    frame.pid = child_pid;
    frame.flags = role_slot;
    if (send_plain(CONTROL_FD, &frame) != FRAME_BYTES) {
        if (kill_and_reap(pidfd, child_pid) != 0)
            protocol_failure(-49, sequence, command->frame.nonce);
        protocol_failure(-50, sequence, command->frame.nonce);
    }

    zero_bytes(&observed, sizeof(observed));
    result = syscall5(SYS_waitid, P_PIDFD, pidfd, (long)&observed,
                      WEXITED | WNOWAIT, 0);
    if (result != 0 || observed.pid != child_pid) {
        if (kill_and_reap(pidfd, child_pid) != 0)
            protocol_failure(-51, sequence, command->frame.nonce);
        protocol_failure(-52, sequence, command->frame.nonce);
    }
    zero_bytes(&consumed, sizeof(consumed));
    result = syscall5(SYS_waitid, P_PIDFD, pidfd, (long)&consumed, WEXITED, 0);
    if (result != 0 || consumed.pid != child_pid ||
        consumed.status != observed.status || consumed.code != observed.code) {
        if (kill_and_reap(pidfd, child_pid) != 0)
            protocol_failure(-53, sequence, command->frame.nonce);
        protocol_failure(-54, sequence, command->frame.nonce);
    }
    zero_bytes(&empty, sizeof(empty));
    result = syscall5(SYS_waitid, P_PIDFD, pidfd, (long)&empty,
                      WEXITED | WNOHANG, 0);
    if (result != -ECHILD) {
        (void)syscall1(SYS_close, pidfd);
        protocol_failure(-55, sequence, command->frame.nonce);
    }
    initialize_frame(&frame, OP_ROLE_REAP, sequence, command->frame.nonce);
    frame.pid = child_pid;
    frame.status = consumed.status;
    frame.flags = (uint32_t)consumed.code;
    frame.fact_a = ECHILD;
    if (send_plain(CONTROL_FD, &frame) != FRAME_BYTES) {
        (void)syscall1(SYS_close, pidfd);
        return -56;
    }
    (void)syscall1(SYS_close, pidfd);
    return 0;
}

static int broker_main(void) {
    struct frame_v2 frame;
    struct received_v2 command;
    struct ucred_v2 guardian_credential;
    uint32_t guardian_credential_bytes = sizeof(guardian_credential);
    int32_t creator_parent_pid = (int32_t)syscall0(SYS_getppid);
    int32_t guardian_pid;
    uint32_t guardian_uid;
    uint32_t guardian_gid;
    int32_t self_pid = (int32_t)syscall0(SYS_getpid);
    uint64_t expected_sequence;
    uint32_t expected_slot;
    int one = 1;
    long result;

    if (syscall5(SYS_prctl, PR_SET_PDEATHSIG, SIGKILL, 0, 0, 0) < 0 ||
        syscall0(SYS_getppid) != creator_parent_pid)
        return 110;
    if (syscall3(SYS_close_range, 4, 0xffffffffU, 0) < 0)
        return 111;
    if (syscall5(SYS_setsockopt, CONTROL_FD, SOL_SOCKET, SO_PASSCRED,
                 (long)&one, sizeof(one)) < 0)
        return 112;
    zero_bytes(&guardian_credential, sizeof(guardian_credential));
    if (syscall5(SYS_getsockopt, CONTROL_FD, SOL_SOCKET, SO_PEERCRED,
                 (long)&guardian_credential,
                 (long)&guardian_credential_bytes) != 0 ||
        guardian_credential_bytes != sizeof(guardian_credential) ||
        guardian_credential.pid <= 0)
        return 113;
    guardian_pid = guardian_credential.pid;
    guardian_uid = guardian_credential.uid;
    guardian_gid = guardian_credential.gid;
    initialize_frame(&frame, OP_BROKER_READY, 0, (const uint8_t *)0);
    frame.pid = self_pid;
    frame.fact_a = (uint64_t)(uint32_t)creator_parent_pid;
    if (send_plain(CONTROL_FD, &frame) != FRAME_BYTES)
        return 114;

    result = receive_frame(CONTROL_FD, &command, guardian_pid, guardian_uid,
                           guardian_gid);
    if (result != 0 || command.fd_count != 0 ||
        !valid_frame(&command.frame, OP_BROKER_GO, 1) ||
        command.frame.pid != self_pid || command.frame.status != 0 ||
        command.frame.flags != 0 || command.frame.fact_a != 0)
        protocol_failure(-20, 1, command.frame.nonce);
    initialize_frame(&frame, OP_BROKER_GO_ECHO, 1, command.frame.nonce);
    frame.pid = self_pid;
    if (send_plain(CONTROL_FD, &frame) != FRAME_BYTES)
        return 115;

    for (expected_sequence = 2, expected_slot = ROLE_WORKER;
         expected_sequence <= 3;
         ++expected_sequence, ++expected_slot) {
        result = receive_frame(CONTROL_FD, &command, guardian_pid,
                               guardian_uid, guardian_gid);
        if (result != 0)
            protocol_failure((int)result, expected_sequence,
                             (const uint8_t *)0);
        if (valid_frame(&command.frame, OP_BROKER_SHUTDOWN, 4) &&
            command.fd_count == 0 && command.frame.pid == self_pid &&
            command.frame.status == 0 && command.frame.flags == 0 &&
            command.frame.fact_a == 0)
            goto shutdown;
        if (!valid_frame(&command.frame, OP_CREATE_ROLE,
                         expected_sequence) ||
            command.frame.pid != self_pid || command.frame.status != 0 ||
            command.frame.flags != 0 ||
            command.frame.fact_a != expected_slot || command.fd_count != 4) {
            close_received(&command);
            protocol_failure(-21, expected_sequence, command.frame.nonce);
        }
        result = create_and_reap_role(
            &command, guardian_pid, guardian_uid, guardian_gid, self_pid,
            expected_slot, expected_sequence
        );
        if (result != 0)
            protocol_failure((int)result, expected_sequence,
                             command.frame.nonce);
    }
    result = receive_frame(CONTROL_FD, &command, guardian_pid, guardian_uid,
                           guardian_gid);
    if (result != 0)
        protocol_failure((int)result, 4, (const uint8_t *)0);
    if (!valid_frame(&command.frame, OP_BROKER_SHUTDOWN, 4) ||
        command.fd_count != 0 || command.frame.pid != self_pid ||
        command.frame.status != 0 || command.frame.flags != 0 ||
        command.frame.fact_a != 0)
        protocol_failure(-22, 4, command.frame.nonce);

shutdown:
    initialize_frame(&frame, OP_BROKER_BYE, 4, command.frame.nonce);
    frame.pid = self_pid;
    if (send_plain(CONTROL_FD, &frame) != FRAME_BYTES)
        return 116;
    (void)syscall1(SYS_close, CONTROL_FD);
    return 0;
}

__attribute__((noreturn)) void _start(void) {
    uint64_t empty_mask = 0;
    int status;
    (void)syscall4(SYS_rt_sigprocmask, SIG_SETMASK, (long)&empty_mask, 0,
                   sizeof(empty_mask));
    status = broker_main();
    syscall1(SYS_exit_group, status);
    __builtin_unreachable();
}
