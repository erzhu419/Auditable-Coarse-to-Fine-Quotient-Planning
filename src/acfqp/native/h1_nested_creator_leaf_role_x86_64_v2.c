/*
 * Source-closed Linux x86-64 WORKER/BUSINESS leaf role image.
 *
 * Build this one source with ACFQP_LEAF_ROLE_SLOT=1 (WORKER) or 2
 * (BUSINESS).  The eventual composed runtime supplies a BROKER as the actual
 * creator/parent, but this standalone leaf image does not attest that parent's
 * executable image or registered role.  An external guardian owns the peer of
 * the AF_UNIX/SOCK_SEQPACKET endpoint installed at fd 3.  The leaf freezes both
 * identities independently: SO_PEERCRED identifies the guardian and getppid()
 * identifies the actual parent PID.  PR_SET_PDEATHSIG binds the leaf lifetime
 * to that parent.  Every command must carry the frozen guardian's
 * SCM_CREDENTIALS.
 *
 *   READY(0, slot, parent) -> GO(1) -> GO_ECHO(1)
 *       -> SHUTDOWN(2) -> BYE(2)
 *
 * This bounded image deliberately contains no worker/business resource
 * semantics and issues no construction, accounting, or official authority.
 */

#include <stdint.h>

#ifndef ACFQP_LEAF_ROLE_SLOT
#error "ACFQP_LEAF_ROLE_SLOT must be 1 (WORKER) or 2 (BUSINESS)"
#endif
#if ACFQP_LEAF_ROLE_SLOT != 1 && ACFQP_LEAF_ROLE_SLOT != 2
#error "invalid ACFQP_LEAF_ROLE_SLOT"
#endif

#define SYS_close 3
#define SYS_getpid 39
#define SYS_sendmsg 46
#define SYS_recvmsg 47
#define SYS_getuid 102
#define SYS_getgid 104
#define SYS_getppid 110
#define SYS_prctl 157
#define SYS_getsockopt 55
#define SYS_exit_group 231
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

#define PR_SET_PDEATHSIG 1
#define SIGKILL 9
#define CONTROL_FD 3
#define FRAME_BYTES 64
#define MAX_CONTROL_BYTES 80

#define FRAME_MAGIC 0x3256524c43514641ULL /* "AFQCLRV2", little endian */
#define FRAME_VERSION 2U

enum opcode_v2 {
    OP_ROLE_READY = 1,
    OP_ROLE_GO = 2,
    OP_ROLE_GO_ECHO = 3,
    OP_ROLE_SHUTDOWN = 4,
    OP_ROLE_BYE = 5,
    OP_PROTOCOL_FAILURE = 6,
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

struct received_v2 {
    struct frame_v2 frame;
    struct ucred_v2 credential;
    uint32_t credential_count;
    uint32_t rights_count;
    uint32_t unknown_count;
};

typedef char frame_must_be_64_bytes[(sizeof(struct frame_v2) == 64) ? 1 : -1];

static inline long syscall0(long number) {
    long result;
    __asm__ volatile("syscall" : "=a"(result) : "a"(number)
                     : "rcx", "r11", "memory");
    return result;
}

static inline long syscall1(long number, long a1) {
    long result;
    __asm__ volatile("syscall" : "=a"(result) : "a"(number), "D"(a1)
                     : "rcx", "r11", "memory");
    return result;
}

static inline long syscall3(long number, long a1, long a2, long a3) {
    long result;
    __asm__ volatile("syscall" : "=a"(result)
                     : "a"(number), "D"(a1), "S"(a2), "d"(a3)
                     : "rcx", "r11", "memory");
    return result;
}

static inline long syscall5(long number, long a1, long a2, long a3,
                            long a4, long a5) {
    register long r10 __asm__("r10") = a4;
    register long r8 __asm__("r8") = a5;
    long result;
    __asm__ volatile("syscall" : "=a"(result)
                     : "a"(number), "D"(a1), "S"(a2), "d"(a3),
                       "r"(r10), "r"(r8)
                     : "rcx", "r11", "memory");
    return result;
}

static inline long syscall6(long number, long a1, long a2, long a3,
                            long a4, long a5, long a6) {
    register long r10 __asm__("r10") = a4;
    register long r8 __asm__("r8") = a5;
    register long r9 __asm__("r9") = a6;
    long result;
    __asm__ volatile("syscall" : "=a"(result)
                     : "a"(number), "D"(a1), "S"(a2), "d"(a3),
                       "r"(r10), "r"(r8), "r"(r9)
                     : "rcx", "r11", "memory");
    return result;
}

static void zero_bytes(void *destination, uint64_t length) {
    uint8_t *bytes = (uint8_t *)destination;
    uint64_t index;
    for (index = 0; index < length; ++index)
        bytes[index] = 0;
}

static void copy_nonce(uint8_t destination[16], const uint8_t source[16]) {
    uint32_t index;
    for (index = 0; index < 16; ++index)
        destination[index] = source[index];
}

static void initialize_frame(struct frame_v2 *frame, uint32_t opcode,
                             uint64_t sequence, int64_t self_pid,
                             uint64_t parent_pid,
                             const uint8_t nonce[16]) {
    zero_bytes(frame, sizeof(*frame));
    frame->magic = FRAME_MAGIC;
    frame->version = FRAME_VERSION;
    frame->opcode = opcode;
    frame->sequence = sequence;
    copy_nonce(frame->nonce, nonce);
    frame->pid = self_pid;
    frame->flags = ACFQP_LEAF_ROLE_SLOT;
    frame->fact_a = parent_pid;
}

static long send_plain(int descriptor, const struct frame_v2 *frame) {
    struct iovec_v2 iov;
    struct msghdr_v2 message;
    zero_bytes(&message, sizeof(message));
    iov.base = (void *)frame;
    iov.length = FRAME_BYTES;
    message.iov = &iov;
    message.iovlen = 1;
    return syscall3(SYS_sendmsg, descriptor, (long)&message, MSG_NOSIGNAL);
}

static long receive_frame(int descriptor, struct received_v2 *received) {
    uint8_t control[MAX_CONTROL_BYTES];
    struct iovec_v2 iov;
    struct msghdr_v2 message;
    struct cmsghdr_v2 *header;
    uint64_t offset;
    long result;

    zero_bytes(received, sizeof(*received));
    zero_bytes(control, sizeof(control));
    zero_bytes(&message, sizeof(message));
    iov.base = &received->frame;
    iov.length = FRAME_BYTES;
    message.iov = &iov;
    message.iovlen = 1;
    message.control = control;
    message.controllen = sizeof(control);
    result = syscall3(SYS_recvmsg, descriptor, (long)&message,
                      MSG_CMSG_CLOEXEC);
    if (result != FRAME_BYTES ||
        (message.flags & (MSG_TRUNC | MSG_CTRUNC)) != 0 ||
        (message.flags & ~(MSG_CMSG_CLOEXEC | MSG_EOR)) != 0)
        return -1;

    offset = 0;
    while (offset + sizeof(struct cmsghdr_v2) <= message.controllen) {
        header = (struct cmsghdr_v2 *)(control + offset);
        if (header->length < sizeof(struct cmsghdr_v2) ||
            offset + header->length > message.controllen)
            return -2;
        if (header->level == SOL_SOCKET && header->type == SCM_CREDENTIALS &&
            header->length == sizeof(struct cmsghdr_v2) +
                                  sizeof(struct ucred_v2)) {
            received->credential = *(struct ucred_v2 *)(header + 1);
            received->credential_count++;
        } else if (header->level == SOL_SOCKET &&
                   header->type == SCM_RIGHTS) {
            received->rights_count +=
                (uint32_t)((header->length - sizeof(*header)) / sizeof(int));
        } else {
            received->unknown_count++;
        }
        offset += (header->length + 7U) & ~7U;
    }
    if (offset != message.controllen)
        return -3;
    return result;
}

static int valid_frame(const struct frame_v2 *frame, uint32_t opcode,
                       uint64_t sequence, int64_t self_pid,
                       uint64_t parent_pid) {
    return frame->magic == FRAME_MAGIC &&
           frame->version == FRAME_VERSION && frame->opcode == opcode &&
           frame->sequence == sequence && frame->pid == self_pid &&
           frame->status == 0 && frame->flags == ACFQP_LEAF_ROLE_SLOT &&
           frame->fact_a == parent_pid;
}

static void protocol_failure(int64_t self_pid, uint64_t parent_pid,
                             uint64_t sequence, int32_t status) {
    struct frame_v2 frame;
    const uint8_t zero_nonce[16] = {0};
    initialize_frame(&frame, OP_PROTOCOL_FAILURE, sequence, self_pid,
                     parent_pid, zero_nonce);
    frame.status = status;
    (void)send_plain(CONTROL_FD, &frame);
    (void)syscall1(SYS_close, CONTROL_FD);
    (void)syscall1(SYS_exit_group, 111);
    for (;;) { }
}

static void leaf_main(void) {
    struct ucred_v2 guardian;
    struct received_v2 command;
    struct frame_v2 frame;
    uint32_t length;
    int32_t socket_type;
    int64_t self_pid;
    int64_t parent_pid;
    uint32_t self_uid;
    uint32_t self_gid;
    const uint8_t zero_nonce[16] = {0};
    long result;

    self_pid = syscall0(SYS_getpid);
    parent_pid = syscall0(SYS_getppid);
    self_uid = (uint32_t)syscall0(SYS_getuid);
    self_gid = (uint32_t)syscall0(SYS_getgid);
    if (self_pid <= 0 || parent_pid <= 0 || self_pid == parent_pid)
        (void)syscall1(SYS_exit_group, 112);

    result = syscall5(SYS_prctl, PR_SET_PDEATHSIG, SIGKILL, 0, 0, 0);
    if (result < 0 || syscall0(SYS_getppid) != parent_pid)
        (void)syscall1(SYS_exit_group, 113);
    if (syscall3(SYS_close_range, 4, 0xffffffffU, 0) < 0)
        (void)syscall1(SYS_exit_group, 114);
    if (syscall5(SYS_setsockopt, CONTROL_FD, SOL_SOCKET, SO_PASSCRED,
                 (long)&(int){1}, sizeof(int)) < 0)
        (void)syscall1(SYS_exit_group, 115);
    length = sizeof(socket_type);
    if (syscall5(SYS_getsockopt, CONTROL_FD, SOL_SOCKET, SO_TYPE,
                 (long)&socket_type, (long)&length) < 0 ||
        length != sizeof(socket_type) || socket_type != SOCK_SEQPACKET)
        (void)syscall1(SYS_exit_group, 116);
    length = sizeof(guardian);
    if (syscall5(SYS_getsockopt, CONTROL_FD, SOL_SOCKET, SO_PEERCRED,
                 (long)&guardian, (long)&length) < 0 ||
        length != sizeof(guardian) || guardian.pid <= 0 ||
        (guardian.pid == self_pid) || guardian.pid == parent_pid ||
        guardian.uid != self_uid || guardian.gid != self_gid)
        (void)syscall1(SYS_exit_group, 117);

    initialize_frame(&frame, OP_ROLE_READY, 0, self_pid,
                     (uint64_t)parent_pid, zero_nonce);
    if (send_plain(CONTROL_FD, &frame) != FRAME_BYTES)
        (void)syscall1(SYS_exit_group, 118);

    result = receive_frame(CONTROL_FD, &command);
    if (result != FRAME_BYTES || command.credential_count != 1 ||
        command.rights_count != 0 || command.unknown_count != 0 ||
        command.credential.pid != guardian.pid ||
        command.credential.uid != guardian.uid ||
        command.credential.gid != guardian.gid ||
        !valid_frame(&command.frame, OP_ROLE_GO, 1, self_pid,
                     (uint64_t)parent_pid))
        protocol_failure(self_pid, (uint64_t)parent_pid, 1, -1);

    initialize_frame(&frame, OP_ROLE_GO_ECHO, 1, self_pid,
                     (uint64_t)parent_pid, command.frame.nonce);
    if (send_plain(CONTROL_FD, &frame) != FRAME_BYTES)
        (void)syscall1(SYS_exit_group, 119);

    result = receive_frame(CONTROL_FD, &command);
    if (result != FRAME_BYTES || command.credential_count != 1 ||
        command.rights_count != 0 || command.unknown_count != 0 ||
        command.credential.pid != guardian.pid ||
        command.credential.uid != guardian.uid ||
        command.credential.gid != guardian.gid ||
        !valid_frame(&command.frame, OP_ROLE_SHUTDOWN, 2, self_pid,
                     (uint64_t)parent_pid))
        protocol_failure(self_pid, (uint64_t)parent_pid, 2, -2);

    initialize_frame(&frame, OP_ROLE_BYE, 2, self_pid,
                     (uint64_t)parent_pid, command.frame.nonce);
    if (send_plain(CONTROL_FD, &frame) != FRAME_BYTES)
        (void)syscall1(SYS_exit_group, 120);
    (void)syscall1(SYS_close, CONTROL_FD);
    (void)syscall1(SYS_exit_group, 0);
    for (;;) { }
}

__attribute__((noreturn, used, section(".text.start")))
void _start(void) {
    leaf_main();
    __builtin_unreachable();
}
