/*
 * Audited Linux x86-64 raw clone3/execveat trampoline for the bounded H1
 * nested-creator SUPERVISOR birth fixture.
 *
 * The guardian calls this symbol through ctypes.PYFUNCTYPE with the GIL held,
 * every signal blocked, and /proc/self/task proving one thread.  The child
 * performs raw syscalls only and never returns to Python or libc.
 *
 * struct h1_supervisor_exec_launch_args_v1 {
 *     struct clone_args *clone_args;       // +0
 *     void *creator_pid_cell_mapping;      // +8
 *     uint64_t pid_cell_mapping_bytes;     // +16
 *     int64_t creator_pid_cell_fd;         // +24
 *     int64_t one_shot_cgroup_grant_fd;    // +32
 *     int64_t child_gate_fd;               // +40
 *     struct native_edge *parent_edge;     // +48
 *     const void *cell_withdrawn_frame;    // +56
 *     uint64_t cell_withdrawn_frame_bytes; // +64
 *     const void *gate_ready_frame;        // +72
 *     uint64_t gate_ready_frame_bytes;     // +80
 *     const void *release_frame;           // +88
 *     uint64_t release_frame_bytes;        // +96
 *     int64_t supervisor_executable_fd;     // +104
 *     char **supervisor_argv;               // +112
 *     char **supervisor_envp;               // +120
 * };
 *
 * struct native_edge {
 *     int64_t clone_result;                // +0
 *     uint64_t status_bits;                // +8
 *     int64_t first_cleanup_error;          // +16
 *     uint64_t reserved_zero;               // +24
 * };
 *
 * status_bits:
 *   1 clone attempted; 2 clone succeeded; 4 clone rejected;
 *   8 parent creator mapping withdrawn; 16 parent creator FD closed;
 *   32 one-shot cgroup grant canonical FD closed;
 *   64 parent supervisor executable FD closed.
 */

        .text
        .globl acfqp_h1_nested_creator_supervisor_exec_birth_v1
        .type acfqp_h1_nested_creator_supervisor_exec_birth_v1,@function
acfqp_h1_nested_creator_supervisor_exec_birth_v1:
        pushq   %r12
        pushq   %r13
        pushq   %r14
        pushq   %r15
        movq    %rdi, %r12
        movq    48(%r12), %r15
        movq    $1, 8(%r15)             /* CLONE_ATTEMPTED */

        movq    0(%r12), %rdi
        movq    $88, %rsi
        movq    $435, %rax              /* clone3 */
        syscall
        testq   %rax, %rax
        jz      .Lchild

        /* Parent and clone-rejection edge share one withdrawal path. */
        movq    %rax, %r13
        movq    %rax, 0(%r15)
        movq    $0, %r14
        testq   %rax, %rax
        js      .Lparent_clone_rejected
        orq     $2, 8(%r15)
        jmp     .Lparent_withdraw
.Lparent_clone_rejected:
        orq     $4, 8(%r15)

.Lparent_withdraw:
        movq    $11, %rax               /* munmap creator PID-cell mapping */
        movq    8(%r12), %rdi
        movq    16(%r12), %rsi
        syscall
        testq   %rax, %rax
        js      .Lparent_munmap_error
        orq     $8, 8(%r15)
        jmp     .Lparent_close_cell
.Lparent_munmap_error:
        movq    %rax, %r14
        movq    %rax, 16(%r15)

.Lparent_close_cell:
        movq    $3, %rax                /* close creator PID-cell FD */
        movq    24(%r12), %rdi
        syscall
        testq   %rax, %rax
        js      .Lparent_cell_close_error
        orq     $16, 8(%r15)
        jmp     .Lparent_close_grant
.Lparent_cell_close_error:
        testq   %r14, %r14
        jnz     .Lparent_close_grant
        movq    %rax, %r14
        movq    %rax, 16(%r15)

.Lparent_close_grant:
        movq    $3, %rax                /* close one-shot cgroup grant FD */
        movq    32(%r12), %rdi
        syscall
        testq   %rax, %rax
        js      .Lparent_grant_close_error
        orq     $32, 8(%r15)
        jmp     .Lparent_close_executable
.Lparent_grant_close_error:
        testq   %r14, %r14
        jnz     .Lparent_close_executable
        movq    %rax, %r14
        movq    %rax, 16(%r15)

.Lparent_close_executable:
        movq    $3, %rax                /* close supervisor executable FD */
        movq    104(%r12), %rdi
        syscall
        testq   %rax, %rax
        js      .Lparent_executable_close_error
        orq     $64, 8(%r15)
        jmp     .Lparent_done
.Lparent_executable_close_error:
        testq   %r14, %r14
        jnz     .Lparent_done
        movq    %rax, %r14
        movq    %rax, 16(%r15)

.Lparent_done:
        testq   %r14, %r14
        jz      .Lparent_return_clone_result
        /* Distinct wrapper failure; the exact clone result remains in edge. */
        movq    %r14, %rax
        subq    $30000, %rax
        jmp     .Lparent_return
.Lparent_return_clone_result:
        movq    %r13, %rax
        jmp     .Lparent_return

.Lchild:
        /* Withdraw both child-side writable PID-cell references. */
        movq    $11, %rax               /* munmap */
        movq    8(%r12), %rdi
        movq    16(%r12), %rsi
        syscall
        testq   %rax, %rax
        js      .Lexit120
        movq    $3, %rax                /* close */
        movq    24(%r12), %rdi
        syscall
        testq   %rax, %rax
        js      .Lexit121

        /* The guardian proves the source gate FD is >3.  FD 3 becomes the
         * only protocol socket; 0..2 remain the inherited standard FDs. */
        movq    $292, %rax              /* dup3(child_gate_fd, 3, 0) */
        movq    40(%r12), %rdi
        movq    $3, %rsi
        xorq    %rdx, %rdx
        syscall
        testq   %rax, %rax
        js      .Lexit122

        /* FD 4 is an exact CLOEXEC executable handle consumed by execveat. */
        movq    $292, %rax              /* dup3(executable_fd, 4, O_CLOEXEC) */
        movq    104(%r12), %rdi
        movq    $4, %rsi
        movq    $0x80000, %rdx
        syscall
        testq   %rax, %rax
        js      .Lexit123
        movq    $436, %rax              /* close_range(5, UINT_MAX, 0) */
        movq    $5, %rdi
        movq    $0xffffffff, %rsi
        xorq    %rdx, %rdx
        syscall
        testq   %rax, %rax
        js      .Lexit124

        /* SOCK_SEQPACKET: every frame is one syscall and must be exact. */
        movq    $44, %rax               /* sendto CELL_WITHDRAWN */
        movq    $3, %rdi
        movq    56(%r12), %rsi
        movq    64(%r12), %rdx
        movq    $0x4000, %r10           /* MSG_NOSIGNAL */
        xorq    %r8, %r8
        xorq    %r9, %r9
        syscall
        testq   %rax, %rax
        js      .Lexit125
        cmpq    64(%r12), %rax
        jne     .Lexit125

        movq    $44, %rax               /* sendto CHILD_GATE_READY */
        movq    $3, %rdi
        movq    72(%r12), %rsi
        movq    80(%r12), %rdx
        movq    $0x4000, %r10
        xorq    %r8, %r8
        xorq    %r9, %r9
        syscall
        testq   %rax, %rax
        js      .Lexit126
        cmpq    80(%r12), %rax
        jne     .Lexit126

        /* Exact no-ancillary RELEASE grammar.  The future wrapper must leave
         * SO_PASSCRED disabled on this child endpoint.  recvmsg receives into
         * expected+1 payload bytes plus a 64-byte control buffer; any extra
         * payload, source address, SCM_RIGHTS, SCM_CREDENTIALS, unknown cmsg,
         * MSG_TRUNC, MSG_CTRUNC, or unknown msg_flag is rejected.
         * MSG_CMSG_CLOEXEC ensures any installed rejected descriptor is
         * CLOEXEC until this child exits.  Linux may echo MSG_CMSG_CLOEXEC in
         * msg_flags and may set MSG_EOR for SOCK_SEQPACKET; those are the only
         * allowed return bits. */
        movq    96(%r12), %rax
        cmpq    $64, %rax
        ja      .Lexit127
        incq    %rax
        subq    $208, %rsp
        movq    %rax, %r13              /* expected+1 payload capacity */
        leaq    0(%rsp), %rdi
        xorq    %rax, %rax
        movq    $26, %rcx
        rep stosq
        leaq    0(%rsp), %rax
        movq    %rax, 72(%rsp)          /* iov_base */
        movq    %r13, 80(%rsp)          /* iov_len */
        leaq    72(%rsp), %rax
        movq    %rax, 104(%rsp)         /* msg_iov */
        movq    $1, 112(%rsp)           /* msg_iovlen */
        leaq    144(%rsp), %rax
        movq    %rax, 120(%rsp)         /* msg_control */
        movq    $64, 128(%rsp)          /* msg_controllen */
        movq    $47, %rax               /* recvmsg */
        movq    $3, %rdi
        leaq    88(%rsp), %rsi          /* msghdr */
        movq    $0x40000000, %rdx       /* MSG_CMSG_CLOEXEC */
        syscall
        testq   %rax, %rax
        js      .Lexit127_with_buffer
        cmpq    96(%r12), %rax
        jne     .Lexit127_with_buffer
        cmpl    $0, 96(%rsp)            /* msg_namelen */
        jne     .Lexit127_with_buffer
        cmpq    $0, 128(%rsp)           /* no ancillary grammar */
        jne     .Lexit127_with_buffer
        movl    136(%rsp), %eax
        movl    %eax, %edx
        andl    $0x28, %edx             /* MSG_TRUNC | MSG_CTRUNC */
        jne     .Lexit127_with_buffer
        andl    $0xbfffff7f, %eax       /* reject bits outside CLOEXEC|EOR */
        jne     .Lexit127_with_buffer

        xorq    %rcx, %rcx
.Lcompare_release:
        cmpq    96(%r12), %rcx
        je      .Lecho_release
        movzbq  (%rsp,%rcx,1), %rax
        movq    88(%r12), %rsi
        movzbq  (%rsi,%rcx,1), %rdx
        cmpq    %rdx, %rax
        jne     .Lexit128_with_buffer
        incq    %rcx
        jmp     .Lcompare_release

.Lecho_release:
        movq    $44, %rax               /* sendto exact READY echo */
        movq    $3, %rdi
        movq    %rsp, %rsi
        movq    96(%r12), %rdx
        movq    $0x4000, %r10
        xorq    %r8, %r8
        xorq    %r9, %r9
        syscall
        testq   %rax, %rax
        js      .Lexit129_with_buffer
        cmpq    96(%r12), %rax
        jne     .Lexit129_with_buffer
        addq    $208, %rsp

        /* Enter the exact sealed supervisor role; a return is failure. */
        subq    $8, %rsp
        movq    $0, (%rsp)
        movq    $322, %rax              /* execveat */
        movq    $4, %rdi
        movq    %rsp, %rsi              /* empty pathname */
        movq    112(%r12), %rdx
        movq    120(%r12), %r10
        movq    $0x1000, %r8            /* AT_EMPTY_PATH */
        xorq    %r9, %r9
        syscall
        addq    $8, %rsp
        movq    $129, %rdi
        movq    $231, %rax              /* exit_group(129) */
        syscall
        ud2

.Lexit127_with_buffer:
        addq    $208, %rsp
        jmp     .Lexit127
.Lexit128_with_buffer:
        addq    $208, %rsp
        jmp     .Lexit128
.Lexit129_with_buffer:
        addq    $208, %rsp
        jmp     .Lexit129

.Lexit120: movq $120, %rdi; jmp .Lexit
.Lexit121: movq $121, %rdi; jmp .Lexit
.Lexit122: movq $122, %rdi; jmp .Lexit
.Lexit123: movq $123, %rdi; jmp .Lexit
.Lexit124: movq $124, %rdi; jmp .Lexit
.Lexit125: movq $125, %rdi; jmp .Lexit
.Lexit126: movq $126, %rdi; jmp .Lexit
.Lexit127: movq $127, %rdi; jmp .Lexit
.Lexit128: movq $128, %rdi; jmp .Lexit
.Lexit129: movq $129, %rdi; jmp .Lexit
.Lexit:
        movq    $231, %rax
        syscall
        ud2

.Lparent_return:
        popq    %r15
        popq    %r14
        popq    %r13
        popq    %r12
        ret
        .size acfqp_h1_nested_creator_supervisor_exec_birth_v1, .-acfqp_h1_nested_creator_supervisor_exec_birth_v1

        .section .note.GNU-stack,"",@progbits
