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
34. Portability
35. portable compiler 
36. bitfields
37. binary operators
38. primitive types
39. [data structures] are systems of [primitive types]
40. arrays
41. control structures
42. memory address
43. 1988 [ansi standard]
44. ## Comparisons
45. bitwise comparisons
46. logical comparisons
47. [bitwise] vs [logical]
48. <=> is the spaceship operator
49. C has less guardrails than high-level languages
50. standards enable efficient collaboration
51. boilerplate
52. c.json boilerplate
53. /* filename.c
54.  * name
55.  * class/course
56.  * date
57.  * /
58. #include <stdio.h>
59. int main() {
60.     printf("hello world!");
61.         return 0;
62. }
63. gcc
    1.  68. gcc -ansi -pedantic -Wall -Wextra [filename].c
64. gdb
65. git
66. ./a.out
67. ## Pointer
    1.  pointer arithmetic
    2.  declarations at the top
    3.  always initialize variables
    4.  uninitialized variables cause to grab previously initialized values from heap
68. $?
69. ## Nonlocal Jumps <setjmp.h>
70. Macro
71. Buffer
72. calling environment
73. ## Common definitions <stddef.h>
74. integral type
75. signed & unsigned types
76. locales
77. digital certificates
78. Strongly typed 