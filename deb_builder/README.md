Below are steps to build qemu/openipmi deb package.
1. For qemu: git clone --recursive
2. If you get error when run step #3, you'll need to resolve dependency. 
   For example, if you get error:

        glib-2.22 gthread-2.0 is required to compile QEMU. 
    
   Please use correct apt source and follow below steps to install glib:
   
        sudo apt-get upgrade 
        sudo apt-get update 
        sudo apt-cache search libglib 
        sudo apt-get install libglib2.0-dev
        
3. Run deb build script.

