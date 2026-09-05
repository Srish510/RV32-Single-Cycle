# Fibonacci Sequence Generator
# Calculates the first 10 Fibonacci numbers and stores them in memory
# Demonstrates R-type, I-type, Branches, Memory Stores, and Pseudo-instructions

.text
.org 0x0000

_start:
    li t0, 0x100      # t0 = Base address in data memory for storing results
    li t1, 10         # t1 = Number of Fibonacci numbers to generate (N = 10)
    
    li a0, 0          # Fib[0] = 0
    li a1, 1          # Fib[1] = 1
    
    sw a0, 0(t0)      # Store Fib[0] at 0x100
    sw a1, 4(t0)      # Store Fib[1] at 0x104
    
    addi t0, t0, 8    # Advance pointer by 8 bytes (2 words)
    addi t1, t1, -2   # Decrement iterations counter by 2

fib_loop:
    beqz t1, end      # If iterations == 0, break out of loop
    
    add a2, a0, a1    # a2 = Fib[N-2] + Fib[N-1]
    sw a2, 0(t0)      # Store new Fibonacci number in memory
    
    # Shift sliding window
    mv a0, a1         # Fib[N-2] = Fib[N-1]
    mv a1, a2         # Fib[N-1] = Fib[N]
    
    addi t0, t0, 4    # Advance memory pointer by 4 bytes (1 word)
    addi t1, t1, -1   # Decrement iteration counter
    
    j fib_loop        # Loop back

end:
    j end             # Infinite spin-loop. Testbench detects this as program completion!
