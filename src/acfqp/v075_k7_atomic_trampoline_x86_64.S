/*
 * Auditable x86-64 clone3 -> Landlock -> execveat trampoline.
 *
 * The parent calls this function with the Python GIL held through
 * ctypes.PYFUNCTYPE.  All Python objects, argv/env arrays and clone_args are
 * prepared before entry.  The child never returns to Python: after clone3 it
 * performs raw syscalls only and ends in execveat or exit_group.
 *
 * struct launch_args {
 *     struct clone_args *clone_args;  // +0
 *     long executable_fd;             // +8
 *     long null_fd;                   // +16
 *     char **argv;                    // +24
 *     char **envp;                    // +32
 *     long expected_parent_pid;       // +40
 *     long landlock_ruleset_fd;       // +48
 *     struct sock_fprog *seccomp;      // +56
 *     long setup_status_fd;            // +64, CLOEXEC
 * };
 */

        .text
        .globl acfqp_k7_clone3_exec
        .type acfqp_k7_clone3_exec,@function
acfqp_k7_clone3_exec:
        pushq   %r12
        movq    %rdi, %r12

        /* clone3(args, sizeof(struct clone_args)) */
        movq    0(%r12), %rdi
        movq    $88, %rsi
        movq    $435, %rax
        syscall
        testq   %rax, %rax
        js      .Lreturn
        jnz     .Lreturn

        /* Child: die if the owning parent disappears, including race window. */
        movq    $157, %rax              /* prctl */
        movq    $1, %rdi                /* PR_SET_PDEATHSIG */
        movq    $9, %rsi                /* SIGKILL */
        xorq    %rdx, %rdx
        xorq    %r10, %r10
        xorq    %r8, %r8
        syscall
        testq   %rax, %rax
        js      .Lpdeath_failed
        movq    $110, %rax              /* getppid */
        syscall
        cmpq    40(%r12), %rax
        jne     .Lparent_race_failed

        /* Irreversibly deny filesystem mutation, including cgroup migration. */
        movq    $157, %rax              /* prctl */
        movq    $38, %rdi               /* PR_SET_NO_NEW_PRIVS */
        movq    $1, %rsi
        xorq    %rdx, %rdx
        xorq    %r10, %r10
        xorq    %r8, %r8
        syscall
        testq   %rax, %rax
        js      .Lnnp_failed
        movq    $446, %rax              /* landlock_restrict_self */
        movq    48(%r12), %rdi
        xorq    %rsi, %rsi
        syscall
        testq   %rax, %rax
        js      .Llandlock_failed

        /* Deny process/thread creation and namespace/parent-tampering calls. */
        movq    $157, %rax              /* prctl */
        movq    $22, %rdi               /* PR_SET_SECCOMP */
        movq    $2, %rsi                /* SECCOMP_MODE_FILTER */
        movq    56(%r12), %rdx
        xorq    %r10, %r10
        xorq    %r8, %r8
        syscall
        testq   %rax, %rax
        js      .Lseccomp_failed

        /* Clear the inherited signal mask before exec. */
        subq    $8, %rsp
        movq    $0, (%rsp)
        movq    $14, %rax               /* rt_sigprocmask */
        movq    $2, %rdi                /* SIG_SETMASK */
        movq    %rsp, %rsi
        xorq    %rdx, %rdx
        movq    $8, %r10
        syscall
        addq    $8, %rsp
        testq   %rax, %rax
        js      .Lsigmask_failed

        /* Bind standard streams to the already-open CLOEXEC /dev/null. */
        movq    $33, %rax               /* dup2 */
        movq    16(%r12), %rdi
        xorq    %rsi, %rsi
        syscall
        testq   %rax, %rax
        js      .Ldup_stdin_failed
        movq    $33, %rax
        movq    16(%r12), %rdi
        movq    $1, %rsi
        syscall
        testq   %rax, %rax
        js      .Ldup_stdout_failed
        movq    $33, %rax
        movq    16(%r12), %rdi
        movq    $2, %rsi
        syscall
        testq   %rax, %rax
        js      .Ldup_stderr_failed

        /* A fixed READY record must precede exec. CLOEXEC EOF then proves
         * exec success; a returned execveat appends its own failure record. */
        xorq    %r8, %r8                /* READY_FOR_EXEC */
        xorq    %r9, %r9                /* errno 0 */
        call    .Lwrite_status
        cmpq    $16, %rax
        jne     .Lexit126

        /* execveat(executable_fd, "", argv, envp, AT_EMPTY_PATH) */
        subq    $8, %rsp
        movq    $0, (%rsp)
        movq    $322, %rax
        movq    8(%r12), %rdi
        movq    %rsp, %rsi
        movq    24(%r12), %rdx
        movq    32(%r12), %r10
        movq    $0x1000, %r8
        xorq    %r9, %r9
        syscall
        addq    $8, %rsp

        /* execveat returned with -errno. */
        movq    %rax, %r9
        negq    %r9
        movq    $10, %r8               /* EXECVEAT */
        call    .Lwrite_status

        /* execveat returned: fail closed with the conventional exec code. */
        movq    $127, %rdi
        movq    $231, %rax              /* exit_group */
        syscall
        ud2

.Lpdeath_failed:
        movq    $1, %r8
        jmp     .Lsyscall_failed126
.Lparent_race_failed:
        movq    $2, %r8
        xorq    %r9, %r9
        call    .Lwrite_status
        jmp     .Lexit126
.Lnnp_failed:
        movq    $3, %r8
        jmp     .Lsyscall_failed126
.Llandlock_failed:
        movq    $4, %r8
        jmp     .Lsyscall_failed126
.Lseccomp_failed:
        movq    $5, %r8
        jmp     .Lsyscall_failed126
.Lsigmask_failed:
        movq    $6, %r8
        jmp     .Lsyscall_failed126
.Ldup_stdin_failed:
        movq    $7, %r8
        jmp     .Lsyscall_failed126
.Ldup_stdout_failed:
        movq    $8, %r8
        jmp     .Lsyscall_failed126
.Ldup_stderr_failed:
        movq    $9, %r8

.Lsyscall_failed126:
        movq    %rax, %r9
        negq    %r9
        call    .Lwrite_status
        jmp     .Lexit126

/* Write one {uint64 stage, uint64 errno} record. Return write(2)'s result. */
.Lwrite_status:
        subq    $16, %rsp
        movq    %r8, 0(%rsp)
        movq    %r9, 8(%rsp)
        movq    $1, %rax                /* write */
        movq    64(%r12), %rdi
        movq    %rsp, %rsi
        movq    $16, %rdx
        syscall
        addq    $16, %rsp
        ret

.Lexit126:
        movq    $126, %rdi
        movq    $231, %rax
        syscall
        ud2

.Lreturn:
        popq    %r12
        ret
        .size acfqp_k7_clone3_exec, .-acfqp_k7_clone3_exec

        .section .note.GNU-stack,"",@progbits
