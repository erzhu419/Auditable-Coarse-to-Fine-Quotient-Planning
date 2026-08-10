/*
 * Source-closed Linux x86-64 supervisor for the bounded H1 two-birth prefix.
 *
 * This is a freestanding, no-libc role image.  The external guardian starts
 * it with one AF_UNIX/SOCK_SEQPACKET control endpoint on fd 3.  The guardian
 * then transfers exactly four CLOEXEC descriptors for PIDFD_PROBE:
 *
 *   0: one-shot CONTROL cgroup grant;
 *   1: writable shared PID-cell memfd;
 *   2: child endpoint of the release gate;
 *   3: creator write-duplicate of the guardian release endpoint.
 *
 * The supervisor itself performs clone3, transfers the resulting pidfd to the
 * guardian, waits for the guardian ACK, releases the inert child, performs
 * WNOWAIT and consuming waitid as the real parent, proves ECHILD, and reports
 * the exact reap facts.  It never creates a second nested child.
 */

#include <stddef.h>
#include <stdint.h>

#define SYS_close 3
#define SYS_mmap 9
#define SYS_munmap 11
#define SYS_rt_sigprocmask 14
#define SYS_getpid 39
#define SYS_sendto 44
#define SYS_sendmsg 46
#define SYS_recvmsg 47
#define SYS_getuid 102
#define SYS_getgid 104
#define SYS_getppid 110
#define SYS_prctl 157
#define SYS_waitid 247
#define SYS_dup3 292
#define SYS_clone3 435
#define SYS_close_range 436
#define SYS_exit_group 231
#define SYS_setsockopt 54

#define SOL_SOCKET 1
#define SCM_RIGHTS 1
#define SCM_CREDENTIALS 2
#define SO_PASSCRED 16
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

#define P_PIDFD 3
#define WNOHANG 1
#define WEXITED 4
#define WNOWAIT 0x01000000
#define ECHILD 10

#define CLONE_PIDFD 0x00001000ULL
#define CLONE_PARENT_SETTID 0x00100000ULL
#define CLONE_CLEAR_SIGHAND 0x100000000ULL
#define CLONE_INTO_CGROUP 0x200000000ULL

#define CONTROL_FD 3
#define CHILD_GATE_FD 4
#define MAX_CONTROL_BYTES 160
#define FRAME_BYTES 64
#define PID_CELL_BYTES 4096

#define FRAME_MAGIC 0x31564e5043514641ULL /* "AFQCPNV1", little endian */
#define FRAME_VERSION 1U

enum opcode_v1 {
    OP_SUPERVISOR_READY = 1,
    OP_PROBE_COMMAND = 2,
    OP_PROBE_PARENT_RETURN = 3,
    OP_PROBE_ACK = 4,
    OP_PROBE_REAP = 5,
    OP_SUPERVISOR_SHUTDOWN = 6,
    OP_SUPERVISOR_BYE = 7,
    OP_PROTOCOL_FAILURE = 8,
    OP_CHILD_CELL_WITHDRAWN = 9,
    OP_CHILD_GATE_READY = 10,
    OP_CHILD_RELEASE = 11,
    OP_CHILD_RELEASE_ECHO = 12,
};

struct frame_v1 {
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

struct iovec_v1 {
    void *base;
    uint64_t length;
};

struct msghdr_v1 {
    void *name;
    uint32_t namelen;
    uint32_t pad0;
    struct iovec_v1 *iov;
    uint64_t iovlen;
    void *control;
    uint64_t controllen;
    uint32_t flags;
    uint32_t pad1;
};

struct cmsghdr_v1 {
    uint64_t length;
    int32_t level;
    int32_t type;
};

struct ucred_v1 {
    int32_t pid;
    uint32_t uid;
    uint32_t gid;
};

struct clone_args_v1 {
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

struct siginfo_v1 {
    int32_t signo;
    int32_t error;
    int32_t code;
    int32_t pad0;
    int32_t pid;
    uint32_t uid;
    int32_t status;
    uint8_t tail[100];
};

struct received_v1 {
    struct frame_v1 frame;
    int32_t fds[4];
    uint32_t fd_count;
    struct ucred_v1 credential;
    uint32_t credential_count;
};

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

static uint64_t aligned_cmsg(uint64_t value) {
    return (value + 7U) & ~7ULL;
}

static int valid_frame(const struct frame_v1 *frame, uint32_t opcode,
                       uint64_t sequence) {
    return frame->magic == FRAME_MAGIC && frame->version == FRAME_VERSION &&
           frame->opcode == opcode && frame->sequence == sequence;
}

static void initialize_frame(struct frame_v1 *frame, uint32_t opcode,
                             uint64_t sequence, const uint8_t *nonce) {
    zero_bytes(frame, sizeof(*frame));
    frame->magic = FRAME_MAGIC;
    frame->version = FRAME_VERSION;
    frame->opcode = opcode;
    frame->sequence = sequence;
    if (nonce != (const uint8_t *)0)
        copy_bytes(frame->nonce, nonce, sizeof(frame->nonce));
}

static long send_plain(int descriptor, const struct frame_v1 *frame) {
    return syscall6(SYS_sendto, descriptor, (long)frame, sizeof(*frame),
                    MSG_NOSIGNAL, 0, 0);
}

static long send_pidfd(int descriptor, const struct frame_v1 *frame,
                       int pidfd) {
    struct iovec_v1 iov;
    struct msghdr_v1 message;
    uint8_t control[24];
    struct cmsghdr_v1 *header;
    zero_bytes(&message, sizeof(message));
    zero_bytes(control, sizeof(control));
    iov.base = (void *)frame;
    iov.length = sizeof(*frame);
    message.iov = &iov;
    message.iovlen = 1;
    message.control = control;
    message.controllen = sizeof(control);
    header = (struct cmsghdr_v1 *)control;
    header->length = 20;
    header->level = SOL_SOCKET;
    header->type = SCM_RIGHTS;
    copy_bytes(control + 16, &pidfd, sizeof(pidfd));
    return syscall3(SYS_sendmsg, descriptor, (long)&message, MSG_NOSIGNAL);
}

static void close_received(struct received_v1 *received) {
    uint32_t index;
    for (index = 0; index < received->fd_count && index < 4; ++index) {
        if (received->fds[index] >= 0)
            syscall1(SYS_close, received->fds[index]);
        received->fds[index] = -1;
    }
    received->fd_count = 0;
}

static int receive_frame(int descriptor, struct received_v1 *received,
                         uint32_t expected_fd_count, int32_t expected_pid,
                         uint32_t expected_uid, uint32_t expected_gid) {
    struct iovec_v1 iov;
    struct msghdr_v1 message;
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
        return -1;
    copy_bytes(&received->frame, payload, FRAME_BYTES);
    offset = 0;
    while (offset + sizeof(struct cmsghdr_v1) <= message.controllen) {
        struct cmsghdr_v1 *header =
            (struct cmsghdr_v1 *)(control + offset);
        uint64_t data_bytes;
        if (header->length < sizeof(*header) ||
            header->length > message.controllen - offset)
            return -2;
        data_bytes = header->length - sizeof(*header);
        if (header->level != SOL_SOCKET)
            return -3;
        if (header->type == SCM_CREDENTIALS) {
            if (data_bytes != sizeof(struct ucred_v1) ||
                received->credential_count != 0)
                return -4;
            copy_bytes(&received->credential, control + offset + 16,
                       sizeof(received->credential));
            received->credential_count = 1;
        } else if (header->type == SCM_RIGHTS) {
            if (data_bytes == 0 || data_bytes % sizeof(int32_t) != 0 ||
                received->fd_count != 0 || data_bytes / sizeof(int32_t) > 4)
                return -5;
            received->fd_count = (uint32_t)(data_bytes / sizeof(int32_t));
            copy_bytes(received->fds, control + offset + 16, data_bytes);
        } else {
            return -6;
        }
        offset += aligned_cmsg(header->length);
    }
    if (offset != aligned_cmsg(message.controllen) &&
        offset != message.controllen)
        return -7;
    if (received->credential_count != 1 ||
        received->credential.pid != expected_pid ||
        received->credential.uid != expected_uid ||
        received->credential.gid != expected_gid ||
        received->fd_count != expected_fd_count)
        return -8;
    return 0;
}

static void protocol_failure(int status, uint64_t sequence,
                             const uint8_t *nonce) {
    struct frame_v1 frame;
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

static void inert_probe_child(int pid_cell_fd, void *pid_mapping,
                              int child_gate_fd, int32_t expected_parent_pid,
                              const uint8_t *nonce, uint64_t sequence) {
    struct frame_v1 withdrawn;
    struct frame_v1 ready;
    struct frame_v1 release;
    struct frame_v1 echo;
    struct received_v1 received;
    long result;
    result = syscall5(SYS_prctl, PR_SET_PDEATHSIG, SIGKILL, 0, 0, 0);
    if (result < 0 || syscall0(SYS_getppid) != expected_parent_pid)
        child_exit(120);
    if (syscall2(SYS_munmap, (long)pid_mapping, PID_CELL_BYTES) < 0)
        child_exit(121);
    if (syscall1(SYS_close, pid_cell_fd) < 0)
        child_exit(122);
    if (child_gate_fd != CHILD_GATE_FD &&
        syscall3(SYS_dup3, child_gate_fd, CHILD_GATE_FD, 0) < 0)
        child_exit(123);
    (void)syscall1(SYS_close, CONTROL_FD);
    if (syscall3(SYS_close_range, 5, 0xffffffffU, 0) < 0)
        child_exit(124);
    initialize_frame(&withdrawn, OP_CHILD_CELL_WITHDRAWN, sequence, nonce);
    withdrawn.pid = syscall0(SYS_getpid);
    if (send_plain(CHILD_GATE_FD, &withdrawn) != FRAME_BYTES)
        child_exit(125);
    initialize_frame(&ready, OP_CHILD_GATE_READY, sequence, nonce);
    ready.pid = withdrawn.pid;
    if (send_plain(CHILD_GATE_FD, &ready) != FRAME_BYTES)
        child_exit(126);

    /* The child endpoint has SO_PASSCRED disabled: RELEASE admits no cmsg. */
    zero_bytes(&received, sizeof(received));
    {
        struct iovec_v1 iov;
        struct msghdr_v1 message;
        uint8_t payload[FRAME_BYTES + 1];
        uint8_t control[64];
        zero_bytes(&message, sizeof(message));
        zero_bytes(payload, sizeof(payload));
        zero_bytes(control, sizeof(control));
        iov.base = payload;
        iov.length = sizeof(payload);
        message.iov = &iov;
        message.iovlen = 1;
        message.control = control;
        message.controllen = sizeof(control);
        result = syscall3(SYS_recvmsg, CHILD_GATE_FD, (long)&message,
                          MSG_CMSG_CLOEXEC);
        if (result != FRAME_BYTES || message.namelen != 0 ||
            message.controllen != 0 ||
            (message.flags & (MSG_TRUNC | MSG_CTRUNC)) != 0 ||
            (message.flags & ~(MSG_CMSG_CLOEXEC | MSG_EOR)) != 0)
            child_exit(127);
        copy_bytes(&release, payload, sizeof(release));
    }
    if (!valid_frame(&release, OP_CHILD_RELEASE, sequence) ||
        !equal_bytes(release.nonce, nonce, 16) || release.pid != withdrawn.pid)
        child_exit(128);
    initialize_frame(&echo, OP_CHILD_RELEASE_ECHO, sequence, nonce);
    echo.pid = withdrawn.pid;
    if (send_plain(CHILD_GATE_FD, &echo) != FRAME_BYTES)
        child_exit(129);
    child_exit(0);
}

static int supervisor_main(void) {
    struct frame_v1 frame;
    struct frame_v1 report;
    struct received_v1 command;
    struct clone_args_v1 clone_args;
    struct siginfo_v1 observed;
    struct siginfo_v1 consumed;
    int32_t guardian_pid = (int32_t)syscall0(SYS_getppid);
    uint32_t guardian_uid = (uint32_t)syscall0(SYS_getuid);
    uint32_t guardian_gid = (uint32_t)syscall0(SYS_getgid);
    int32_t self_pid = (int32_t)syscall0(SYS_getpid);
    int one = 1;
    int pidfd = -1;
    int pid_cell_fd;
    int cgroup_fd;
    int child_gate_fd;
    int release_fd;
    int32_t child_pid;
    void *pid_mapping;
    long result;

    if (syscall5(SYS_setsockopt, CONTROL_FD, SOL_SOCKET, SO_PASSCRED,
                 (long)&one, sizeof(one)) < 0)
        return 111;
    initialize_frame(&frame, OP_SUPERVISOR_READY, 0, (const uint8_t *)0);
    frame.pid = self_pid;
    frame.fact_a = (uint64_t)(uint32_t)guardian_pid;
    if (send_plain(CONTROL_FD, &frame) != FRAME_BYTES)
        return 112;

    result = receive_frame(CONTROL_FD, &command, 4, guardian_pid, guardian_uid,
                           guardian_gid);
    if (result != 0)
        protocol_failure((int)result, 1, (const uint8_t *)0);
    if (!valid_frame(&command.frame, OP_PROBE_COMMAND, 1) ||
        command.frame.pid != self_pid)
        protocol_failure(-20, 1, command.frame.nonce);
    cgroup_fd = command.fds[0];
    pid_cell_fd = command.fds[1];
    child_gate_fd = command.fds[2];
    release_fd = command.fds[3];

    pid_mapping = (void *)syscall6(SYS_mmap, 0, PID_CELL_BYTES,
                                   PROT_READ | PROT_WRITE, MAP_SHARED,
                                   pid_cell_fd, 0);
    if (pid_mapping == MAP_FAILED || (intptr_t)pid_mapping < 0)
        protocol_failure(-21, 1, command.frame.nonce);
    zero_bytes(&clone_args, sizeof(clone_args));
    clone_args.flags = CLONE_PIDFD | CLONE_PARENT_SETTID |
                       CLONE_CLEAR_SIGHAND | CLONE_INTO_CGROUP;
    clone_args.pidfd = (uint64_t)(uintptr_t)&pidfd;
    clone_args.parent_tid = (uint64_t)(uintptr_t)pid_mapping;
    clone_args.exit_signal = SIGCHLD;
    clone_args.cgroup = (uint64_t)(uint32_t)cgroup_fd;
    result = syscall2(SYS_clone3, (long)&clone_args, sizeof(clone_args));
    if (result == 0)
        inert_probe_child(pid_cell_fd, pid_mapping, child_gate_fd, self_pid,
                          command.frame.nonce, 1);
    child_pid = (int32_t)result;
    (void)syscall2(SYS_munmap, (long)pid_mapping, PID_CELL_BYTES);
    (void)syscall1(SYS_close, pid_cell_fd);
    (void)syscall1(SYS_close, cgroup_fd);
    (void)syscall1(SYS_close, child_gate_fd);
    command.fds[0] = -1;
    command.fds[1] = -1;
    command.fds[2] = -1;
    command.fds[3] = release_fd;
    command.fd_count = 4;
    if (result <= 0 || pidfd < 0) {
        close_received(&command);
        protocol_failure((int)result, 1, command.frame.nonce);
    }

    initialize_frame(&report, OP_PROBE_PARENT_RETURN, 1,
                     command.frame.nonce);
    report.pid = child_pid;
    report.status = 0;
    report.flags = 0x1fU; /* clone + both parent withdrawals + grant close */
    report.fact_a = (uint64_t)(uint32_t)self_pid;
    if (send_pidfd(CONTROL_FD, &report, pidfd) != FRAME_BYTES) {
        close_received(&command);
        protocol_failure(-22, 1, command.frame.nonce);
    }

    {
        struct received_v1 ack;
        result = receive_frame(CONTROL_FD, &ack, 0, guardian_pid, guardian_uid,
                               guardian_gid);
        if (result != 0 || !valid_frame(&ack.frame, OP_PROBE_ACK, 1) ||
            !equal_bytes(ack.frame.nonce, command.frame.nonce, 16) ||
            ack.frame.pid != child_pid) {
            close_received(&ack);
            close_received(&command);
            protocol_failure(-23, 1, command.frame.nonce);
        }
    }
    initialize_frame(&frame, OP_CHILD_RELEASE, 1, command.frame.nonce);
    frame.pid = child_pid;
    if (send_plain(release_fd, &frame) != FRAME_BYTES) {
        close_received(&command);
        protocol_failure(-24, 1, command.frame.nonce);
    }
    (void)syscall1(SYS_close, release_fd);
    command.fds[3] = -1;
    command.fd_count = 0;

    zero_bytes(&observed, sizeof(observed));
    result = syscall5(SYS_waitid, P_PIDFD, pidfd, (long)&observed,
                      WEXITED | WNOWAIT, 0);
    if (result != 0 || observed.pid != child_pid || observed.status != 0)
        protocol_failure(-25, 1, command.frame.nonce);
    zero_bytes(&consumed, sizeof(consumed));
    result = syscall5(SYS_waitid, P_PIDFD, pidfd, (long)&consumed, WEXITED, 0);
    if (result != 0 || consumed.pid != child_pid || consumed.status != 0 ||
        consumed.code != observed.code)
        protocol_failure(-26, 1, command.frame.nonce);
    zero_bytes(&frame, sizeof(frame));
    result = syscall5(SYS_waitid, P_PIDFD, pidfd, (long)&frame,
                      WEXITED | WNOHANG, 0);
    if (result != -ECHILD)
        protocol_failure(-27, 1, command.frame.nonce);
    initialize_frame(&report, OP_PROBE_REAP, 1, command.frame.nonce);
    report.pid = child_pid;
    report.status = consumed.status;
    report.flags = (uint32_t)consumed.code;
    report.fact_a = ECHILD;
    if (send_plain(CONTROL_FD, &report) != FRAME_BYTES)
        protocol_failure(-28, 1, command.frame.nonce);
    (void)syscall1(SYS_close, pidfd);

    result = receive_frame(CONTROL_FD, &command, 0, guardian_pid, guardian_uid,
                           guardian_gid);
    if (result != 0 ||
        !valid_frame(&command.frame, OP_SUPERVISOR_SHUTDOWN, 2) ||
        command.frame.pid != self_pid)
        protocol_failure(-29, 2, command.frame.nonce);
    initialize_frame(&frame, OP_SUPERVISOR_BYE, 2, command.frame.nonce);
    frame.pid = self_pid;
    if (send_plain(CONTROL_FD, &frame) != FRAME_BYTES)
        return 113;
    (void)syscall1(SYS_close, CONTROL_FD);
    return 0;
}

__attribute__((noreturn)) void _start(void) {
    uint64_t empty_mask = 0;
    int status;
    (void)syscall4(SYS_rt_sigprocmask, SIG_SETMASK, (long)&empty_mask, 0,
                   sizeof(empty_mask));
    status = supervisor_main();
    syscall1(SYS_exit_group, status);
    __builtin_unreachable();
}
