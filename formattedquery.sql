
SELECT distinct
    A.ID as ProdutID,
    A.LASTNAME AS Surname, A.FIRSTNAME || ' ' || A.MIDDLENAME  AS Given_Name,
    (SELECT TYPE FROM EDLVRS.GENDER WHERE ID = A.GENDER_ID) AS Sex, TO_CHAR (a.dateofbirthad,'DD-MM-YYYY') AS Date_of_birth,
    'Government of Nepal' as Nationality,
    (select TO_CHAR(MIN(CAST(issuedate AS DATE)), 'DD-MM-YYYY')  from edlvrs.licensedetail where newlicenseno=ld.newlicenseno) as Date_of_issue,
    TO_CHAR(LD.EXPIRYDATE , 'DD-MM-YYYY')  AS Date_of_expiry,
    
    A.CITIZENSHIPNUMBER as Citizenship_No,
    A.PASSPORTNUMBER as Passport_No,
    'Photo\'||A.id||'.jpg ' as Photo,
    A.MOBILENUMBER as Contact_No,
    (select name from edlvrs.licenseissueoffice WHERE ID=ld.licenseissueoffice_id )AS License_Office,
    A.WITNESSFIRSTNAME || ' ' || NVL(A.WITNESSMIDDLENAME,'') || ' ' || A.WITNESSLASTNAME AS FH_Name,
    (SELECT NAME FROM EDLVRS.DISTRICT WHERE ID = AD.DISTRICT_ID) AS Region,
    
    (SELECT NAME FROM EDLVRS.VILLAGEMETROCITY WHERE ID = ad.VILLAGEMETROCITY_ID)||','||ad.tole||'-'||ad.wardnumber AS Street_House_Number,
     
      (SELECT TYPE FROM EDLVRS.BLOODGROUP WHERE ID = A.BLOODGROUP_ID) AS BG,
    LD.NEWLICENSENO as Driving_License_No,
    (Select name from edlvrs.country where id=AD.Country_id)as Country,

    -- CATEGORY FIXED: AGGREGATED ONLY ONCE
    (SELECT LISTAGG(tcl.type, ', ') WITHIN GROUP (ORDER BY tcl.type)
     FROM edlvrs.licensedetail dl
     JOIN edlvrs.licensecategory cl ON cl.licensedetail_id = dl.id
     JOIN edlvrs.licensecategorytype tcl ON tcl.id = cl.lisccategorytype_id
     WHERE dl.newlicenseno = LD.newlicenseno
    ) AS Category,  
    'Sign1\'||A.id||'.jpg' AS Signature1,
    'Sign2\'||A.id||'.jpg' As Signature2
FROM EDLVRS.LICENSEDETAIL LD
JOIN EDLVRS.LICENSE L
    ON LD.LICENSE_ID = L.ID
JOIN EDLVRS.APPLICANT A
    ON L.APPLICANT_ID = A.ID
LEFT JOIN EDLVRS.ADDRESS AD
    ON A.ID = AD.APPLICANT_ID

WHERE LD.NEWLICENSENO IN (


) 

AND LD.expirydate = ( SELECT MAX(expirydate)
        FROM EDLVRS.LICENSEDETAIL
        WHERE LICENSE_ID = L.ID
        having ld.expirydate > sysdate
        )
and ld.issuedate=(
       SELECT MAX(issuedate)
        FROM EDLVRS.LICENSEDETAIL
        WHERE LICENSE_ID = L.ID)
and ad.addresstype='PERM'
  
