import Image from "next/image";

export const LogoPrebel = () => {
  return (
    <section>
      <Image
        src="/image/Prebel_AzulClaro_SF.webp"
        alt="Logo Prebel Azul claro"
        className="justify-self-end block dark:hidden"
        width={100}
        height={100}
      />
      <Image
        src="/image/Prebel_Blanco.webp"
        alt="Logo Prebel Azul claro"
        className="justify-self-end hidden dark:block"
        width={100}
        height={100}
      />
    </section>
  );
};
