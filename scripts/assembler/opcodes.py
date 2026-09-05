
# Opcodes (instruction[6:0])
OP_R_TYPE  = 0b0110011
OP_I_TYPE  = 0b0010011
OP_LOAD    = 0b0000011
OP_STORE   = 0b0100011
OP_BRANCH  = 0b1100011
OP_JAL     = 0b1101111
OP_JALR    = 0b1100111
OP_LUI     = 0b0110111
OP_AUIPC   = 0b0010111

# funct3 values keyed by mnemonic
FUNCT3 = {
    # R-type / I-type ALU
    'add': 0b000, 'addi': 0b000,
    'sub': 0b000,
    'sll': 0b001, 'slli': 0b001,
    'slt': 0b010, 'slti': 0b010,
    'sltu': 0b011, 'sltiu': 0b011,
    'xor': 0b100, 'xori': 0b100,
    'srl': 0b101, 'srli': 0b101,
    'sra': 0b101, 'srai': 0b101,
    'or': 0b110, 'ori': 0b110,
    'and': 0b111, 'andi': 0b111,
    # Load
    'lb': 0b000, 'lh': 0b001, 'lw': 0b010,
    'lbu': 0b100, 'lhu': 0b101,
    # Store
    'sb': 0b000, 'sh': 0b001, 'sw': 0b010,
    # Branch
    'beq': 0b000, 'bne': 0b001,
    'blt': 0b100, 'bge': 0b101,
    'bltu': 0b110, 'bgeu': 0b111,
    # JALR
    'jalr': 0b000,
}

# funct7 values for R-type instructions
FUNCT7 = {
    'add': 0b0000000, 'sub': 0b0100000,
    'sll': 0b0000000, 'slt': 0b0000000, 'sltu': 0b0000000,
    'xor': 0b0000000, 'srl': 0b0000000, 'sra': 0b0100000,
    'or': 0b0000000, 'and': 0b0000000,
}

# funct7 for shift-immediate instructions (SLLI, SRLI, SRAI)
FUNCT7_SHIFT = {
    'slli': 0b0000000,
    'srli': 0b0000000,
    'srai': 0b0100000,
}

# Instruction groupings for dispatch
R_TYPE_INSTRS = {'add', 'sub', 'sll', 'slt', 'sltu', 'xor', 'srl', 'sra', 'or', 'and'}
I_TYPE_ALU    = {'addi', 'slti', 'sltiu', 'xori', 'ori', 'andi'}
I_TYPE_SHIFT  = {'slli', 'srli', 'srai'}
LOAD_INSTRS   = {'lb', 'lh', 'lw', 'lbu', 'lhu'}
STORE_INSTRS  = {'sb', 'sh', 'sw'}
BRANCH_INSTRS = {'beq', 'bne', 'blt', 'bge', 'bltu', 'bgeu'}
