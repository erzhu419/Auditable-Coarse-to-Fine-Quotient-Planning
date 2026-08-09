/*
 * Audit source only.  B2-B never assembles, maps, or invokes this file.
 *
 * A later slice may turn a separately reviewed byte-for-byte successor into
 * an executable trampoline.  The intended ABI is Linux x86_64 clone3:
 *
 *     rax = 435 (SYS_clone3)
 *     rdi = pointer to struct clone_args
 *     rsi = 88 (registered structure size)
 *
 * This source deliberately exports no symbol and contains no instruction.
 * Its retained bytes are sealed into the bounded B2-B source closure only.
 */
