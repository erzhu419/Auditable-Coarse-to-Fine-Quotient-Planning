/*
 * Source-closed Linux x86-64 supervisor V2 command-loop image.
 *
 * The V1 source is an explicit, digest-pinned build input.  Its helpers and
 * exact SUPERVISOR -> PIDFD_PROBE protocol are reused here without changing
 * the V1 source or image.  V2 replaces only the entry state machine: after
 * the probe has been creator-reaped and ECHILD has been proved, the role can
 * either shut down immediately (the V1-compatible path) or consume one exact
 * four-descriptor BROKER command.  In the latter branch the SUPERVISOR is the
 * sole clone3/execveat creator and WNOWAIT/consuming reaper of BROKER.  The
 * present construction slice verifies the source/image and replays only the
 * V1-compatible probe-reaped shutdown branch; a later lease-bound slice owns
 * activation and authority for the BROKER branch.
 */

#define supervisor_main supervisor_main_v1_embedded
#define _start h1_nested_creator_supervisor_v1_embedded_start
#include "h1_nested_creator_supervisor_x86_64_v1.c"
#undef _start
#undef supervisor_main

#define SYS_execveat 322
#define SYS_fcntl 72
#define SYS_getsockopt 55
#define SYS_kill 62
#define SYS_lseek 8
#define SYS_pidfd_send_signal 424
#define SYS_pread64 17
#define AT_EMPTY_PATH 0x1000
#define ECHILD_V2 10
#define ESRCH_V2 3
#define FD_CLOEXEC 1
#define F_GETFD 1
#define F_GETFL 3
#define F_GET_SEALS 1034
#define O_PATH 010000000
#define P_PID 1
#define REQUIRED_BROKER_ELF_SEALS 15
#define SEEK_END 2
#define SEEK_SET 0
#define SO_TYPE 3
#define SO_PEERCRED 17
#define SOCK_SEQPACKET 5
#define O_CLOEXEC 02000000
#define BROKER_CHANNEL_FD 3
#define BROKER_EXECUTABLE_FD 4
#define BROKER_ELF_BYTE_COUNT 12720

#define OP_BROKER_COMMAND 13
#define OP_BROKER_PARENT_RETURN 14
#define OP_BROKER_ACK 15
#define OP_BROKER_ACK_ECHO 16
#define OP_BROKER_REAP 17

static int all_zero_bytes(const void *source, uint64_t count) {
    const uint8_t *in = (const uint8_t *)source;
    uint64_t index;
    uint8_t observed = 0;
    for (index = 0; index < count; ++index)
        observed |= in[index];
    return observed == 0;
}

static int validate_broker_command_descriptors(
    const struct received_v1 *command, int32_t guardian_pid,
    uint32_t guardian_uid, uint32_t guardian_gid) {
    uint8_t elf_identity[20];
    int socket_type = 0;
    uint32_t socket_type_bytes = sizeof(socket_type);
    struct ucred_v1 channel_peer;
    uint32_t channel_peer_bytes = sizeof(channel_peer);
    uint32_t left;
    uint32_t right;
    if (command->fd_count != 4)
        return -1;
    for (left = 0; left < 4; ++left) {
        if (command->fds[left] < 0 ||
            syscall2(SYS_fcntl, command->fds[left], F_GETFD) != FD_CLOEXEC)
            return -2;
        for (right = left + 1; right < 4; ++right) {
            if (command->fds[left] == command->fds[right])
                return -3;
        }
    }
    if ((syscall2(SYS_fcntl, command->fds[0], F_GETFL) & O_PATH) != O_PATH)
        return -8;
    if (syscall2(SYS_fcntl, command->fds[1], F_GET_SEALS) != 0 ||
        syscall3(SYS_lseek, command->fds[1], 0, SEEK_END) != PID_CELL_BYTES ||
        syscall3(SYS_lseek, command->fds[1], 0, SEEK_SET) != 0)
        return -4;
    if (syscall2(SYS_fcntl, command->fds[2], F_GET_SEALS) !=
            REQUIRED_BROKER_ELF_SEALS ||
        syscall3(SYS_lseek, command->fds[2], 0, SEEK_END) !=
            BROKER_ELF_BYTE_COUNT ||
        syscall3(SYS_lseek, command->fds[2], 0, SEEK_SET) != 0)
        return -5;
    zero_bytes(elf_identity, sizeof(elf_identity));
    if (syscall4(SYS_pread64, command->fds[2], (long)elf_identity,
                 sizeof(elf_identity), 0) != sizeof(elf_identity) ||
        elf_identity[0] != 0x7f || elf_identity[1] != 'E' ||
        elf_identity[2] != 'L' || elf_identity[3] != 'F' ||
        elf_identity[4] != 2 || elf_identity[5] != 1 ||
        elf_identity[6] != 1 || elf_identity[16] != 2 ||
        elf_identity[17] != 0 || elf_identity[18] != 0x3e ||
        elf_identity[19] != 0)
        return -6;
    if (syscall5(SYS_getsockopt, command->fds[3], SOL_SOCKET, SO_TYPE,
                 (long)&socket_type, (long)&socket_type_bytes) != 0 ||
        socket_type_bytes != sizeof(socket_type) ||
        socket_type != SOCK_SEQPACKET)
        return -7;
    zero_bytes(&channel_peer, sizeof(channel_peer));
    if (syscall5(SYS_getsockopt, command->fds[3], SOL_SOCKET, SO_PEERCRED,
                 (long)&channel_peer, (long)&channel_peer_bytes) != 0 ||
        channel_peer_bytes != sizeof(channel_peer) ||
        channel_peer.pid != guardian_pid || channel_peer.uid != guardian_uid ||
        channel_peer.gid != guardian_gid)
        return -9;
    return 0;
}

static int kill_consume_prove_close_broker(int pidfd, int32_t child_pid) {
    struct siginfo_v1 consumed;
    struct siginfo_v1 no_child;
    long result;
    int idtype;
    int id;
    int valid = 1;
    if (child_pid <= 0)
        return -1;
    if (pidfd >= 0) {
        idtype = P_PIDFD;
        id = pidfd;
        result = syscall4(SYS_pidfd_send_signal, pidfd, SIGKILL, 0, 0);
    } else {
        idtype = P_PID;
        id = child_pid;
        result = syscall2(SYS_kill, child_pid, SIGKILL);
    }
    if (result != 0 && result != -ESRCH_V2)
        valid = 0;
    zero_bytes(&consumed, sizeof(consumed));
    result = syscall5(SYS_waitid, idtype, id, (long)&consumed, WEXITED, 0);
    if (result != 0 || consumed.pid != child_pid)
        valid = 0;
    zero_bytes(&no_child, sizeof(no_child));
    result = syscall5(SYS_waitid, idtype, id, (long)&no_child,
                      WEXITED | WNOHANG, 0);
    if (result != -ECHILD_V2)
        valid = 0;
    if (pidfd >= 0 && syscall1(SYS_close, pidfd) != 0)
        valid = 0;
    return valid ? 0 : -1;
}

static int prove_consumed_and_close_broker(int pidfd) {
    struct siginfo_v1 no_child;
    long result;
    int valid = 1;
    zero_bytes(&no_child, sizeof(no_child));
    result = syscall5(SYS_waitid, P_PIDFD, pidfd, (long)&no_child,
                      WEXITED | WNOHANG, 0);
    if (result != -ECHILD_V2)
        valid = 0;
    if (syscall1(SYS_close, pidfd) != 0)
        valid = 0;
    return valid ? 0 : -1;
}

static void broker_protocol_failure_after_clone(
    int status, const uint8_t *nonce, int pidfd, int32_t child_pid) {
    if (kill_consume_prove_close_broker(pidfd, child_pid) != 0)
        status = -41;
    protocol_failure(status, 2, nonce);
}

/* Exact copy of receive_frame's parser with a two-valued post-probe arity. */
static int receive_post_probe_command(int descriptor,
                                      struct received_v1 *received,
                                      int32_t expected_pid,
                                      uint32_t expected_uid,
                                      uint32_t expected_gid) {
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
        (received->fd_count != 0 && received->fd_count != 4))
        return -8;
    return 0;
}

static void broker_exec_child(int pid_cell_fd, void *pid_mapping,
                              int cgroup_fd, int executable_fd,
                              int broker_channel_fd,
                              int32_t expected_parent_pid) {
    char argv0[] = "acfqp-h1-broker-v2";
    char empty[] = "";
    char *argv[2];
    char *envp[1];
    long result;
    result = syscall5(SYS_prctl, PR_SET_PDEATHSIG, SIGKILL, 0, 0, 0);
    if (result < 0 || syscall0(SYS_getppid) != expected_parent_pid)
        child_exit(130);
    if (syscall2(SYS_munmap, (long)pid_mapping, PID_CELL_BYTES) < 0)
        child_exit(131);
    if (syscall1(SYS_close, pid_cell_fd) < 0 ||
        syscall1(SYS_close, cgroup_fd) < 0)
        child_exit(132);
    if (broker_channel_fd != BROKER_CHANNEL_FD &&
        syscall3(SYS_dup3, broker_channel_fd, BROKER_CHANNEL_FD, 0) < 0)
        child_exit(133);
    if (executable_fd != BROKER_EXECUTABLE_FD &&
        syscall3(SYS_dup3, executable_fd, BROKER_EXECUTABLE_FD,
                 O_CLOEXEC) < 0)
        child_exit(134);
    if (syscall3(SYS_close_range, 5, 0xffffffffU, 0) < 0)
        child_exit(135);
    argv[0] = argv0;
    argv[1] = (char *)0;
    envp[0] = (char *)0;
    (void)syscall5(SYS_execveat, BROKER_EXECUTABLE_FD, (long)empty,
                   (long)argv, (long)envp, AT_EMPTY_PATH);
    child_exit(136);
}

static int supervisor_main_v2(void) {
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
    uint64_t shutdown_sequence = 2;

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
    report.flags = 0x1fU;
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

    /* V2 additive seam: direct shutdown or one exact BROKER birth/reap. */
    result = receive_post_probe_command(CONTROL_FD, &command, guardian_pid,
                                        guardian_uid, guardian_gid);
    if (result != 0)
        protocol_failure((int)result, 2, (const uint8_t *)0);
    if (valid_frame(&command.frame, OP_BROKER_COMMAND, 2)) {
        int broker_cgroup_fd = command.fds[0];
        int broker_pid_cell_fd = command.fds[1];
        int broker_executable_fd = command.fds[2];
        int broker_channel_fd = command.fds[3];
        int broker_pidfd = -1;
        int32_t broker_pid;
        void *broker_pid_mapping;
        int descriptor_validation;
        if (command.fd_count != 4 || command.frame.pid != self_pid ||
            command.frame.status != 0 || command.frame.flags != 0 ||
            command.frame.fact_a != 0)
            protocol_failure(-29, 2, command.frame.nonce);
        descriptor_validation = validate_broker_command_descriptors(
            &command, guardian_pid, guardian_uid, guardian_gid
        );
        if (descriptor_validation != 0) {
            close_received(&command);
            protocol_failure(-42 + descriptor_validation, 2,
                             command.frame.nonce);
        }
        broker_pid_mapping = (void *)syscall6(
            SYS_mmap, 0, PID_CELL_BYTES, PROT_READ | PROT_WRITE, MAP_SHARED,
            broker_pid_cell_fd, 0);
        if (broker_pid_mapping == MAP_FAILED ||
            (intptr_t)broker_pid_mapping < 0 ||
            !all_zero_bytes(broker_pid_mapping, PID_CELL_BYTES)) {
            close_received(&command);
            protocol_failure(-30, 2, command.frame.nonce);
        }
        zero_bytes(&clone_args, sizeof(clone_args));
        clone_args.flags = CLONE_PIDFD | CLONE_PARENT_SETTID |
                           CLONE_CLEAR_SIGHAND | CLONE_INTO_CGROUP;
        clone_args.pidfd = (uint64_t)(uintptr_t)&broker_pidfd;
        clone_args.parent_tid = (uint64_t)(uintptr_t)broker_pid_mapping;
        clone_args.exit_signal = SIGCHLD;
        clone_args.cgroup = (uint64_t)(uint32_t)broker_cgroup_fd;
        result = syscall2(SYS_clone3, (long)&clone_args, sizeof(clone_args));
        if (result == 0)
            broker_exec_child(broker_pid_cell_fd, broker_pid_mapping,
                              broker_cgroup_fd, broker_executable_fd,
                              broker_channel_fd, self_pid);
        broker_pid = (int32_t)result;
        if (result > 0 &&
            (*(volatile int32_t *)broker_pid_mapping != broker_pid ||
             !all_zero_bytes((const uint8_t *)broker_pid_mapping + 4,
                             PID_CELL_BYTES - 4))) {
            (void)syscall2(SYS_munmap, (long)broker_pid_mapping,
                           PID_CELL_BYTES);
            close_received(&command);
            broker_protocol_failure_after_clone(
                -31, command.frame.nonce, broker_pidfd, broker_pid
            );
        }
        (void)syscall2(SYS_munmap, (long)broker_pid_mapping, PID_CELL_BYTES);
        close_received(&command);
        if (result > 0 && broker_pidfd < 0)
            broker_protocol_failure_after_clone(
                -43, command.frame.nonce, broker_pidfd, broker_pid
            );
        if (result <= 0) {
            if (broker_pidfd >= 0)
                (void)syscall1(SYS_close, broker_pidfd);
            protocol_failure((int)result, 2, command.frame.nonce);
        }

        initialize_frame(&report, OP_BROKER_PARENT_RETURN, 2,
                         command.frame.nonce);
        report.pid = broker_pid;
        report.status = 0;
        report.flags = 0x1fU;
        report.fact_a = (uint64_t)(uint32_t)self_pid;
        if (send_pidfd(CONTROL_FD, &report, broker_pidfd) != FRAME_BYTES)
            broker_protocol_failure_after_clone(
                -32, command.frame.nonce, broker_pidfd, broker_pid
            );
        {
            struct received_v1 broker_ack;
            result = receive_frame(CONTROL_FD, &broker_ack, 0, guardian_pid,
                                   guardian_uid, guardian_gid);
            if (result != 0 ||
                !valid_frame(&broker_ack.frame, OP_BROKER_ACK, 2) ||
                !equal_bytes(broker_ack.frame.nonce,
                             command.frame.nonce, 16) ||
                broker_ack.frame.pid != broker_pid ||
                broker_ack.frame.status != 0 ||
                broker_ack.frame.flags != 0 ||
                broker_ack.frame.fact_a != 0) {
                close_received(&broker_ack);
                broker_protocol_failure_after_clone(
                    -33, command.frame.nonce, broker_pidfd, broker_pid
                );
            }
        }
        initialize_frame(&frame, OP_BROKER_ACK_ECHO, 2,
                         command.frame.nonce);
        frame.pid = broker_pid;
        if (send_plain(CONTROL_FD, &frame) != FRAME_BYTES)
            broker_protocol_failure_after_clone(
                -34, command.frame.nonce, broker_pidfd, broker_pid
            );

        zero_bytes(&observed, sizeof(observed));
        result = syscall5(SYS_waitid, P_PIDFD, broker_pidfd, (long)&observed,
                          WEXITED | WNOWAIT, 0);
        if (result != 0 || observed.pid != broker_pid)
            broker_protocol_failure_after_clone(
                -35, command.frame.nonce, broker_pidfd, broker_pid
            );
        zero_bytes(&consumed, sizeof(consumed));
        result = syscall5(SYS_waitid, P_PIDFD, broker_pidfd, (long)&consumed,
                          WEXITED, 0);
        if (result != 0)
            broker_protocol_failure_after_clone(
                -36, command.frame.nonce, broker_pidfd, broker_pid
            );
        if (consumed.pid != broker_pid ||
            consumed.status != observed.status ||
            consumed.code != observed.code) {
            if (prove_consumed_and_close_broker(broker_pidfd) != 0)
                protocol_failure(-41, 2, command.frame.nonce);
            protocol_failure(-36, 2, command.frame.nonce);
        }
        zero_bytes(&frame, sizeof(frame));
        result = syscall5(SYS_waitid, P_PIDFD, broker_pidfd, (long)&frame,
                          WEXITED | WNOHANG, 0);
        if (result != -ECHILD) {
            (void)syscall1(SYS_close, broker_pidfd);
            protocol_failure(-37, 2, command.frame.nonce);
        }
        initialize_frame(&report, OP_BROKER_REAP, 2,
                         command.frame.nonce);
        report.pid = broker_pid;
        report.status = consumed.status;
        report.flags = (uint32_t)consumed.code;
        report.fact_a = ECHILD;
        if (send_plain(CONTROL_FD, &report) != FRAME_BYTES) {
            (void)syscall1(SYS_close, broker_pidfd);
            protocol_failure(-38, 2, command.frame.nonce);
        }
        if (syscall1(SYS_close, broker_pidfd) != 0)
            protocol_failure(-44, 2, command.frame.nonce);
        shutdown_sequence = 3;
        result = receive_frame(CONTROL_FD, &command, 0, guardian_pid,
                               guardian_uid, guardian_gid);
        if (result != 0)
            protocol_failure((int)result, shutdown_sequence,
                             (const uint8_t *)0);
    }
    if (command.fd_count != 0)
        protocol_failure(-39, shutdown_sequence, command.frame.nonce);
    if (!valid_frame(&command.frame, OP_SUPERVISOR_SHUTDOWN,
                     shutdown_sequence) || command.frame.pid != self_pid)
        protocol_failure(-40, shutdown_sequence, command.frame.nonce);
    initialize_frame(&frame, OP_SUPERVISOR_BYE, shutdown_sequence,
                     command.frame.nonce);
    frame.pid = self_pid;
    if (send_plain(CONTROL_FD, &frame) != FRAME_BYTES)
        return 114;
    (void)syscall1(SYS_close, CONTROL_FD);
    return 0;
}

__attribute__((noreturn)) void _start(void) {
    uint64_t empty_mask = 0;
    int status;
    (void)syscall4(SYS_rt_sigprocmask, SIG_SETMASK, (long)&empty_mask, 0,
                   sizeof(empty_mask));
    status = supervisor_main_v2();
    syscall1(SYS_exit_group, status);
    __builtin_unreachable();
}
