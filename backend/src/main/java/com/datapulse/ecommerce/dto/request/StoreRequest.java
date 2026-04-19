package com.datapulse.ecommerce.dto.request;

public class StoreRequest {
    private String name, description, address, email, ownerEmail, ownerPassword;

    public String getName()          { return name; }           public void setName(String v)          { this.name = v; }
    public String getDescription()   { return description; }    public void setDescription(String v)   { this.description = v; }
    public String getAddress()       { return address; }        public void setAddress(String v)        { this.address = v; }
    public String getEmail()         { return email; }          public void setEmail(String v)          { this.email = v; }
    public String getOwnerEmail()    { return ownerEmail; }     public void setOwnerEmail(String v)     { this.ownerEmail = v; }
    public String getOwnerPassword() { return ownerPassword; }  public void setOwnerPassword(String v)  { this.ownerPassword = v; }
}
