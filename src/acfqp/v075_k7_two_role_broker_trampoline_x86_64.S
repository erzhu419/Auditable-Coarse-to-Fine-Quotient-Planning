/*
 * Two-role broker clone3 trampoline.  The child path is identical to the
 * audited V0-107 no-spawn trampoline.  On a positive parent return, the
 * role-specific write-ahead cell is set before control returns to Python.
 *
 * struct launch_args {
 *   struct clone_args *clone_args; long executable_fd; long null_fd;
 *   char **argv; char **envp; long expected_parent_pid;
 *   long landlock_ruleset_fd; struct sock_fprog *seccomp;
 *   long setup_status_fd; uint64_t *role_edge_cell;
 *   int64_t *clone_result_cell;
 * };
 */
        .text
        .globl acfqp_k7_two_role_clone3_exec
        .type acfqp_k7_two_role_clone3_exec,@function
acfqp_k7_two_role_clone3_exec:
        pushq   %r12
        movq    %rdi, %r12
        movq    0(%r12), %rdi
        movq    $88, %rsi
        movq    $435, %rax
        syscall
        testq   %rax, %rax
        js      .Lparent_rejected
        jz      .Lchild
        movq    72(%r12), %rdx
        movq    $1, (%rdx)
        movq    80(%r12), %rdx
        movq    %rax, (%rdx)
        jmp     .Lreturn
.Lparent_rejected:
        movq    80(%r12), %rdx
        movq    %rax, (%rdx)
        jmp     .Lreturn

.Lchild:
        movq    $157, %rax
        movq    $1, %rdi
        movq    $9, %rsi
        xorq    %rdx, %rdx
        xorq    %r10, %r10
        xorq    %r8, %r8
        syscall
        testq   %rax, %rax
        js      .Lpdeath_failed
        movq    $110, %rax
        syscall
        cmpq    40(%r12), %rax
        jne     .Lparent_race_failed
        movq    $157, %rax
        movq    $38, %rdi
        movq    $1, %rsi
        xorq    %rdx, %rdx
        xorq    %r10, %r10
        xorq    %r8, %r8
        syscall
        testq   %rax, %rax
        js      .Lnnp_failed
        movq    $446, %rax
        movq    48(%r12), %rdi
        xorq    %rsi, %rsi
        syscall
        testq   %rax, %rax
        js      .Llandlock_failed
        movq    $157, %rax
        movq    $22, %rdi
        movq    $2, %rsi
        movq    56(%r12), %rdx
        xorq    %r10, %r10
        xorq    %r8, %r8
        syscall
        testq   %rax, %rax
        js      .Lseccomp_failed
        subq    $8, %rsp
        movq    $0, (%rsp)
        movq    $14, %rax
        movq    $2, %rdi
        movq    %rsp, %rsi
        xorq    %rdx, %rdx
        movq    $8, %r10
        syscall
        addq    $8, %rsp
        testq   %rax, %rax
        js      .Lsigmask_failed
        movq    $33, %rax
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
        xorq    %r8, %r8
        xorq    %r9, %r9
        call    .Lwrite_status
        cmpq    $16, %rax
        jne     .Lexit126
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
        movq    %rax, %r9
        negq    %r9
        movq    $10, %r8
        call    .Lwrite_status
        movq    $127, %rdi
        movq    $231, %rax
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
.Lwrite_status:
        subq    $16, %rsp
        movq    %r8, 0(%rsp)
        movq    %r9, 8(%rsp)
        movq    $1, %rax
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
        .size acfqp_k7_two_role_clone3_exec, .-acfqp_k7_two_role_clone3_exec
        .section .note.GNU-stack,"",@progbits
