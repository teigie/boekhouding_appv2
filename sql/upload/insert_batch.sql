-- Insert one raw uploaded row into temp_afschrift2. Executed once per row
-- (executemany) for an account's batch, inside the transaction that the
-- balance-chain/dedup checks in this same folder then validate.
-- Params: :Datum, :Naam, :Rekening, :Tegenrekening, :Code, :Af_bij,
--         :Bedrag_eur, :Mutatiesoort, :Mededeling, :Saldo_na_mutatie, :Tag

INSERT INTO temp_afschrift2
    (Datum, Naam, Rekening, Tegenrekening, Code, Af_bij, Bedrag_eur,
     Mutatiesoort, Mededeling, Saldo_na_mutatie, Tag)
VALUES
    (:Datum, :Naam, :Rekening, :Tegenrekening, :Code, :Af_bij, :Bedrag_eur,
     :Mutatiesoort, :Mededeling, :Saldo_na_mutatie, :Tag);
