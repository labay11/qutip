#This file is part of QuTIP.
#
#    QuTIP is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#    QuTIP is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with QuTIP.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright (C) 2011, Paul D. Nation & Robert J. Johansson
#
###########################################################################
import numpy as np
class Codegen():
    """
    Class for generating cython code files at runtime.
    """
    def __init__(self,hterms,tdterms,hconst=None,tab="\t"):
        self.hterms=hterms
        self.tdterms=tdterms
        self.hconst=hconst
        self.code=[]
        self.tab=tab
        self.level=0
        self.func_list=dir(np.math)[4:-1]
    #write lines of code to self.code
    def write(self,string):
        self.code.append(self.tab*self.level+string+"\n")
    #open file called filename for writing    
    def file(self,filename):
        self.file=open(filename,"w")
    #generate the file    
    def generate(self,filename="rhs.pyx"):
        self.time_vars()
        for line in cython_preamble()+cython_checks()+self.func_header():
            self.write(line)
        self.indent()
        for line in self.func_vars():
            self.write(line)
        for line in self.func_for():
            self.write(line)
        self.write(self.func_end())
        self.dedent()
        for line in cython_checks()+cython_spmv()+cython_checks()+parallel_cython_spmv():
            self.write(line)
        self.file(filename)
        self.file.writelines(self.code)
        self.file.close()
    #increase indention level by one
    def indent(self):
        self.level+=1
    #decrease indention level by one
    def dedent(self):
        if self.level==0:
            raise SyntaxError("Error in code generator")
        self.level-=1
    def func_header(self):
        """
        Creates function header for time-dependent ODE RHS.
        """
        func_name="def cyq_td_ode_rhs("
        input_vars="float t, np.ndarray[CTYPE_t, ndim=1] vec, " #strings for time and vector variables
        input_vars+="np.ndarray[CTYPE_t, ndim=2] data"+", np.ndarray[int, ndim=2] idx"+", np.ndarray[int, ndim=2] ptr"
        func_end="):"
        return [func_name+input_vars+func_end]
    def time_vars(self):
        """
        Rewrites time-dependent parts to include np.
        """
        out_td=[]
        for jj in range(len(self.tdterms)):
            text=self.tdterms[jj]
            any_np=np.array([text.find(x) for x in self.func_list])
            ind=np.nonzero(any_np>-1)[0]
            for kk in ind:
                new_text='np.'+self.func_list[kk]
                text=text.replace(self.func_list[kk],new_text)
            self.tdterms[jj]=text
            
    def func_vars(self):
        """
        Writes the variables and their types & spmv parts
        """
        func_vars=["",'cdef Py_ssize_t row','cdef int num_rows = len(vec)','cdef np.ndarray[CTYPE_t, ndim=2] out = np.zeros((num_rows,1),dtype=np.complex)']
        if self.hconst:
            td_consts=self.hconst.items()
            for elem in td_consts:
                kind=type(elem[1]).__name__
                func_vars.append("cdef "+kind+" "+elem[0]+" = "+str(elem[1]))
        func_vars.append(" ") #add a spacer line between variables and Hamiltonian components.
        for ht in range(self.hterms):
            hstr=str(ht)
            str_out="cdef np.ndarray[CTYPE_t, ndim=2] Hvec"+hstr+" = "+"spmv(data["+hstr+"],"+"idx["+hstr+"],"+"ptr["+hstr+"],"+"vec"+")"
            if ht!=0:
                str_out+="*"+self.tdterms[ht-1]
            func_vars.append(str_out)
        return func_vars
    def func_for(self):
        """
        Writes function for-loop
        """
        func_terms=["","for row in range(num_rows):"]
        sum_string="\tout[row,0] = Hvec0[row,0]"
        for ht in range(1,self.hterms):
            sum_string+=" + Hvec"+str(ht)+"[row,0]"
        func_terms.append(sum_string)
        return func_terms
    def func_end(self):
        return "return out"
        
        
def cython_preamble():
    """
    Returns list of strings for standard Cython file preamble.
    """
    line0="# This file is generated automatically by QuTiP. (c)2011 Paul D. Nation & J. R. Johansson"
    line1="import numpy as np"
    line2="cimport numpy as np"
    line3="cimport cython"
    line4="from cython.parallel cimport prange"
    line5=""
    line6="ctypedef np.complex128_t CTYPE_t"
    line7="ctypedef np.float64_t DTYPE_t"
    return [line0,line1,line2,line3,line4,line5,line6,line7]

def cython_checks():
    """
    List of strings that turn off Cython checks.
    """
    line0=""
    line1=""
    line2="@cython.boundscheck(False)"
    line3="@cython.wraparound(False)"
    return [line0,line1,line2,line3]


def cython_spmv():
    """
    Writes SPMV function.
    """
    line0="def spmv(np.ndarray[CTYPE_t, ndim=1] data, np.ndarray[int] idx,np.ndarray[int] ptr,np.ndarray[CTYPE_t, ndim=1] vec):"
    line1="\tcdef Py_ssize_t row"
    line2="\tcdef int jj,row_start,row_end"
    line3="\tcdef int num_rows=len(vec)"
    line4="\tcdef complex dot"
    line5="\tcdef np.ndarray[CTYPE_t, ndim=2] out = np.zeros((num_rows,1),dtype=np.complex)"
    line6="\tfor row in range(num_rows):"
    line7="\t\tdot=0.0"
    line8="\t\trow_start = ptr[row]"
    line9="\t\trow_end = ptr[row+1]"
    lineA="\t\tfor jj in range(row_start,row_end):"
    lineB="\t\t\tdot=dot+data[jj]*vec[idx[jj]]"
    lineC="\t\tout[row,0]=dot"
    lineD="\treturn out"
    return [line0,line1,line2,line3,line4,line5,line6,line7,line8,line9,lineA,lineB,lineC,lineD]

def parallel_cython_spmv():
    """
    Writes parallel SPMV function.
    """
    line0="def parallel_spmv(np.ndarray[CTYPE_t, ndim=1] data, np.ndarray[int] idx,np.ndarray[int] ptr,np.ndarray[CTYPE_t, ndim=1] vec):"
    line1="\tcdef Py_ssize_t row"
    line2="\tcdef int jj,row_start,row_end"
    line3="\tcdef int num_rows=len(vec)"
    line4="\tcdef complex dot"
    line5="\tcdef np.ndarray[CTYPE_t, ndim=2] out = np.zeros((num_rows,1),dtype=np.complex)"
    line6="\tfor row in prange(num_rows,nogil=True):"
    line7="\t\tdot=0.0"
    line8="\t\trow_start = ptr[row]"
    line9="\t\trow_end = ptr[row+1]"
    lineA="\t\tfor jj in range(row_start,row_end):"
    lineB="\t\t\tdot=dot+data[jj]*vec[idx[jj]]"
    lineC="\t\tout[row,0]=dot"
    lineD="\treturn out"
    return [line0,line1,line2,line3,line4,line5,line6,line7,line8,line9,lineA,lineB,lineC,lineD]


if __name__=="__main__":
    import numpy
    import pyximport;pyximport.install(setup_args={'include_dirs':[numpy.get_include()]})
    cgen=Codegen([1,2],['t'])
    cgen.generate()
    #from rhs import cyq_td_ode_rhs
    code = compile('from rhs import cyq_td_ode_rhs', '<string>', 'exec')
    exec(code)

    
