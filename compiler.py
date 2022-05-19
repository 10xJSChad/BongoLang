import re

f = open("main.drum", "r")
code = f.readlines()

asm = []
data = []
functions = []
function_stack = [None]
macros = [
    "%macro write_string 2 ",
        "mov   eax, 4",
        "mov   ebx, 1",
        "mov   ecx, %1",
        "mov   edx, %2",
        "int   80h",
    "%endmacro",    
]

def get_function_index_from_name(function_name):
    for i, x in enumerate(functions):
        if x[0] == function_name:
            return(i)
        
def create_function_if_nonexistent(function_name):
    #[None, []]
    exists = False
    for x in functions:
        if x[0] == function_name:
            exists = True
    
    if not exists:
        functions.append([function_name, []])

def asm_append(line, ignore_stack=False):
    #print(line, function_stack[0])
    func = function_stack[0]
    if func == None or ignore_stack:
        asm.append(line)
    elif func != None:
        functions[get_function_index_from_name(func)][1].append(line)


def get_variable_name(line, enclose=False, allownone=False):
    variable_name = re.search(r'.*?\$(.*)\$.*' , line)
    if variable_name:
        if enclose:
            return("[" + variable_name.group(1) + "]")
        else:
            return(variable_name.group(1))
        
    if allownone:
        return None
    return line

def if_statement(line, index):
    instruction = None
    instructions = {
        "==": "je",
        ">": "jg",
        "<": "jl",
        ">=": "jge",
        "<=": "jle",
        "!=": "jne"
    }
    
    args = re.split('>|<|==|>=|<=|!=|\n', line[3:])
    function_name = "if_" + str(index)
    for i, x in enumerate(args):
        args[i] = args[i].replace('=', '').strip()
        args[i] = get_variable_name(args[i], enclose=True)
        if args[i] == "": args.pop(i)
    
    for x in instructions:
        if x in line: instruction = instructions[x]
        
    asm_append("mov eax, " + str(args[1]))
    asm_append("cmp " + str(args[0]) + ", eax")
    asm_append(instruction + " " + function_name)
    
    function_stack.insert(0, function_name)
    create_function_if_nonexistent(function_name)
    asm_append(function_name + "_return:", ignore_stack=True)

def variable_operation(line):
    line = line.replace(" ", "")
    operation = None
    operations = ["+", "-", "*", "/", "="]
    a = b = None
    
    for x in operations:
        if x in line:
            operation = x
            line_split = line.split(operation)
            a = get_variable_name(line_split[0], enclose=True).strip()
            b = get_variable_name(line_split[1], enclose=True).strip()
            break
    
    asm_append("mov eax, " + b) 
    if operation == "+":
        asm_append("add " + a + ", eax")
    if operation == "-":
        asm_append("sub " + a + ", eax")
    if operation == "=":
        asm_append("mov " + a + ", eax")
    #print(a + operation + b)
    
def end_statement():
    function_stack.pop(0)

def print_statement(line):
    variable_name = get_variable_name(line)
    asm_append("write_string " + variable_name + ", " + variable_name + "len")

def goto_statement(line):
    asm_append(line.replace("goto", "jmp").lstrip().rstrip())    
    
def string_declaration(line):
    string_name = line.split()[1]
    string_value = line[line.index("=")+1:].lstrip().rstrip('\n')
    data.append("\n" + string_name + " db \"" + string_value + "\"")
    data.append("\n" + string_name + "len equ $ - " + string_name)

def numeral_declaration(line):
    numeral_name = line.split()[1]
    numeral_value = line[line.index("=")+1:].lstrip().rstrip('\n')
    data.append("\n" + numeral_name + " dd " + numeral_value + "")

def label_declaration(line):
    asm_append(line.split()[1] + ":")

def parse_lines(lines):
    for i, line in enumerate(lines):
        line_split = line.split()
        if(line_split):
            keyword = line_split[0]
        else: keyword = "N/A"
        
        if keyword == "string":
            string_declaration(line)         
        if keyword == "numeral":
            numeral_declaration(line)  
        if keyword == "print":
            print_statement(line)          
        if keyword == "label":
            label_declaration(line)
        if keyword == "goto":
            goto_statement(line)
        if keyword == "if":
            if_statement(line, i)
        if keyword == "end":
            end_statement()
        if get_variable_name(keyword, allownone=True):
            variable_operation(line)

def compile():
    parse_lines(code)
    result = ""
    #Add macros
    for x in macros:
        result += "\n" + x
        
    #Add functions
    for x in functions:
        result += "\n\n" + x[0] + ":"
        for y in x[1]:
            result += "\n" + y
        result += "\njmp " + x[0] + "_return"
        
    result += "\n\nglobal _start\n_start:"
    for x in asm:
        result += "\n" + x 
    result += "\nmov eax, 1\nint 0x80"
    
    #Build data section
    result += "\nsection .data"
    for x in data:
        result += x
    return result
           
print(compile())