const ProductLayout = ({ children }: { children: React.ReactNode }) => {
  return (
    <div>
        <section className="h-[400px] flex flex-col justify-center items-center w-full relative bg-[url('/assets/product-hero.png')] bg-cover bg-center">
                <div className="absolute inset-0 bg-black/40"></div>
                <div className="z-20">
                    <h1 className="max-[1200px]:text-[32px] text-[40px] font-work-sans font-semibold text-center">3-in-1 Portable Travel Water Bottle</h1>
                    {/* <p className="max-[1200px]:text-[16px] text-[20px] font-public-sans font-light text-center">The exclusive heart of the Elite Pack experience. </p> */}
                </div>
        </section>
      {children}
    </div>
  )
};

export default ProductLayout;