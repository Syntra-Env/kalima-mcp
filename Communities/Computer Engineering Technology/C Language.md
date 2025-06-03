0. # C Language
1. strict procedural language
2. ## ANSI C standard
3. problem solving (debugging)
   1. "entering from multiple doors"
4. problem decomposition
   1. small testable components
   2. data-function coupling
5. # Architecture
6. is like a contract with developers
7. memory management
8.  parsing
9.  data structures (more in second half)
10. code/variable tracing
11. command line
12. parsing command line
13. makefiles
14. modular programming
15. scales of complexity
16. assembly language
17. processor
18. processor architecture
19. ## Comments
20. C comments = alt+shift+A = block comments = /* */
21. conventions
22. comments conventions
23. comment during the process of writing code
24. include comments to reference oonline code used
25. 1972 - Dennis Ritchie
26. Multix
27. Time sharing
28. ken thompson
29. libraries
30. statically linked library
31. dynamically linked / shared library
32. Unix
33. compiler
34. Link: combines object files, creates a single executable
35. Portability
36. portable compiler 
37. bitfields
38. binary operators
39. primitive types
40. [data structures] are systems of [primitive types]
41. arrays
42. control structures
43. memory address
44. 1988 [ansi standard]
45. ## Comparisons
46. bitwise comparisons
47. logical comparisons
48. [bitwise] vs [logical]
49. <=> is the spaceship operator
50. C has less guardrails than high-level languages
51. standards enable efficient collaboration
52. boilerplate
53. c.json boilerplate
54. /* filename.c
55.  * name
56.  * class/course
57.  * date
58.  * /
59. #include <stdio.h>
60. int main() { printf("hello world!"); return 0; }
61. gcc
    1.  gcc -ansi -pedantic -Wall -Wextra -o [executableFileName] [sourceCodeFilename].c
    2.  -E option: shows the code after the preprocessed defines are pasted everywhere they need to be in the code.
62. gdb
63. git
64. ./a.out
65. ## Pointer
    1.  pointer arithmetic
    2.  declarations at the top
    3.  always initialize variables
    4.  uninitialized variables cause to grab previously initialized values from heap
66. $?
67. ## Nonlocal Jumps <setjmp.h>
68. Macro: text replacement?
69. Buffer
70. calling environment
71. ## Common definitions <stddef.h>
72. integral type
73. signed & unsigned types
74. locales
75. digital certificates
76. Strongly typed
77. # Week 4
78. ## Print
    1.  - -> \0
    2.  '*'
    3.  '\n'
79. Procedure can only do one thing
    1.  separation of concerns
80. Preprocessor directives: don't take any memory???
    1.  #define
    2.  #include
81. if (argc != 3) error = 1;
82. namespaceL where names are reserved
    1.  memory location
    2.  offsets: from wherever you are in the stack currently
        1.  when we use an offset, we're gonna add that many to the side of the memory location
        2.  when it passes location in memory, does it pass the first location? is the offset then the side of that item in memory and used to determined the next freely available space in memory?
    3.  type: symbol table
    4.  bounds checking: if you go outside the array, you might get a segmentation error/fault (if you're lucky).
        1.  outside domain of OS, where it does not take care of memory allocation
    5.  string termination symbol: null: \0 -> "__" <- \0
83. What's the difference between the method prototype and method declaration?
84. method declaration: returnType functionName (type name pair(s)) {}
85. is the offest related to pointer arithmetic?
86. when you say it's good to initialize a variable because anything could be in it, do you mean it could be assigned a memory location that hasn't been freed before?
87. in which order are elements stored in the symbol item? does it have to do with how the program will be executed?
88. ## while vs for loop
89. for loop when you know when you want to loop to end
90. while loop when you don't know exactly when the loop will end or should end
91. while(string[i++] != '\0'); return i-1;
92. Union: single value, multiple types
93. Struct: multiple different values as a new type: takes care of the memory allocation for us: not necessarily contiguous in memory, could store its parts in different places in memory.
94. ## common input problems
95. snippet library: things you do over and over again:
96.  printf:
    1.  format specifiers (%%):
        1.  %12s, %7s, %6s
        2.  %[flags][width][precision][type_letter]
        3.  %d, %i (signed integer)
        4.  %u (unsigned integer) (gives us one more bit)
        5.  %f (real numbers)
        6.  %c (character)
        7.  %s (string)
        8.  %x (hex)
        9.  %lx (long hex value)
        10. %o (octal)
97.  ### stream: 
    1.  input is parsing things that are coming to you on a stream
    2.  it is a path
    3.  examples
        1.  files
        2.  user input
        3.  http calls
    4.  handled by interrupts: pauses. stores environment and loads new environment then goes back to stored environment.
        1.  context switches: very costly, should be used sparsely
    5.  scanf: not useful since we can't trust users to follow the rules of the game
        1.  if there's nothing in the stream, it's going to stop and wait for an input
        2.  will take whatever was in the buffer/stream (like new line)
        3.  SOLUTION: flush the buffer when you'd like the stream to be reset and not include any previously unintentionally stored inputs in the stream. \n\r
    6.  &number = "give me address of 'number'" 
98.  Can use swtich case statement for fallthrough operations (if you don't want it to break after a case) that apply the same process for some inputs, with slight differences... sort of like method overloading
99.  ## Labels
100. thispart:
101. goto thispart; // jump routine
102. one instruction fits in one register/word/architecture bit size
103. Static Functions
     1.   available in the file in which they're defined
     2.   avoiding namespace collisions
53. ## Four-part algorithm structure
    1.  input stage
    2.  validation stage
    3.  processing stage
    4.  output stage
54. code for each stage should be kept distinct
55. don't write duplicate of any stage
56. Syntax: how code is parsed, revered words, what the compiler expects to see
57. volatile
58. typedef
59. extern
60. goto
61. register
62. union
63. struct
64. 1 register = 1 word in the processor architecture 
65. word: architecture size (bits) (e.g., x32, x64, etc)
66. most significant bit [signed/unsigned]
67. 2's complement
68. type qualifiers
69. interpreted vs uninterpreted languages
70. sizeof can be used to cast to different types (type = size)
71. variables: named locations in memory
72. bit field interpretor
73. how many bits is a memory location?
74. indirection
75. registers don't have an address
76. name -> reference to first bit of an address -> type
77. type represents size of memory

| type   | size (in bits) |
| ------ | -------------- |
| int    | 16 or 32       | words fit easily, so no multiple
| float  | 32             |
| char   | 8              |
| double | 64             |

- use char for bool?
- literals for constants
- #define star '*'
- address offset + pointer math + primitive
- *<type> address size *
- pointer operator
- function call operator
- '->'
- bitwise shift operator: change representation + shortcut
- '?' ternator boolean operator (spaceship operator?)
- control register
- static: off the stack (in heap)
- heap memory is not cleared automatically
- typedef char bool: defining new type
- complex variables
- reg stack pointer
- segmentation fall error

- compilation process
- preprocessing
- compilation
- linking
- loading
- run program
- GNU compiler colelction
- ansi american national standards institute
- standards aids portability between compilers
- #define preprocessor directives
- stdlib
- return vs exit: return returns from current function call while exit is a system call that terminates current process
- exit takes an integer parameter that represents the exit static (success/failure)
- atexit()
- a C function may not return an array
- omitted return value in C89= return int
- non-voiid function -> produces value
- order of function definition: based on which methods call each other and in which order; very important for successful compilation
- function prototypes
- changes to parameters during execution
- fprintf
- conversion specifications [formatting]
- &num means that memory location of variable is being passed rather than copy of variable.
- EOF: input error before data can be read

1.   ## Week 5
2.   indirection
3.   pointers
4.   & = address-of operator
5.   * = indirection operator/pointer/dereferencing operator: takes address and looks what's inside it. it accesses the actual value at the position of the pointer.
6.   pointer types
7.   generic pointer = [void * pointer = null;] : doesn't have a size, requires type casting
     1.   stores an address
     2.   all pointers are the same size but can point to things of different sizes.
     3.   initialized pointers to null: makes nullpointer errors catchable
8.   Register keyword used with a pointer makes the pointer unavailable. If the pointer is stored in the register, it is not in memory.
9.   malloc returns null generic pointer
10.  char** pointer of pointers memory addresses to characters
11.  how come list of addresses are not necessarily contiguous?

## method tracing
#ifndef NULL // prevents namespace collision
    #define NULL (void*) 0
#endif
variables
int number = 0;
int * pointer = NULL;
pointer = &number; // address to number
*pointer = 12; // uses pointer to change value at location it points to

- pointer size on your system
- tracing 
- programming another function in a different file 

memory leak: memory we can't find to clean up. OS memory leaks stay permanently. causes heap to overtake the stack (heap overflow)

## Dynamic Memory Allocation
1. void * malloc(bytes): allocates heap memory. Returns void pointer to the start of the heap memory. takes (size_t size). faster than calloc
2.void * calloc(int number, size_t size): allocates contiguous heap memory. tries to zero out/empty/clean up all the memory allocated.
3. void * realloc(void * ptr, size_t size): copy memory once found, gives pointer to free if allocation is successful. used for resizing (usually for making it bigger).
   1. ptr = malloc(ptr, (sizeof(char)*4) :: not good, destroys original ptr and becomes null if it fails, and original memory is no longer accessible.
4. free()
5. size_t = the size of a type
6. assign null pointer to freed memory so we don't accidentally try to reference it.
7. ? what's the difference between dynamic memory allocation and static memory allocation?
8. name of the array is equal to its address
   1. offset notation
9. if all pointers point to an address, and all addresses are the same size, then what is the purpose of having different pointer types? Perhaps information useful for actual allocation of data in that memory location
10. pointer arithmetic: first need to define a unit of a pointer: what is number 1 in pointers: this depends on the pointer type

#include <stdio.h>

int main (){
    bob = (char *)malloc(sizeof(char) * 16);

    for (i=0;i<16;i++) 
        *(bob + i) = i + 'A';

    printf("%c and %\n", (char)*bob, (char)*(bob+3));

    return 0;
}

## Favorite Numbers Program
1. dynamically allocate and reallocate (to add numbers) memory as an array
2.  check number against list
3.  input number
4.  free the allocated memory while keeping empty list or something we can still display after freeing memory

5. until (exit): {
   1. display menu
   2. take choice
      1. display
         1. takes list
         2. return
         3. prints list[i]
         4. define termination condition
      2. add 
         1. prompt user to enter #
         2. take #
         3. check #
         4. add # to list
      3. purge
         1. free memory
         2. recreate empty list
      4. exit
         1. print exit message
         2. end program
6. }

favnum.c {
    #include <stdio.h>
    #include <stdlib.h>

    #define FALSE 0

    void displaylist( int * thelist) {

        /*  input: list of ints 
            return: void
            function: prints the list until it hits -1
        */

        while(*thelist != -1)
            printf("%i", *(thelist++)); // increments the number in the list
        printf("\n");

        return;
    }

    int main() {
        // create an empty list (empty is -1)

        char exit = FALSE; // using char because it's the smallest type we can use
        int * numberlist = (int *)malloc(sizeof(int));

        *numberlist = -1;
       
       
        while (!exit) {

            // show menu

            scanf("%d", &choice);
            // get choice

            // switch on choice
                // display list
            
             displaylist(numberlist); // copy of address that points to something that already exists

             exit = !exit; // or !FALSE

        } 
    }
}

The unary operator & is said to be only applicable to objects in memory.
> It cannot be applied to expressions, constants, or register variables.
How come the above are not objects in memory?




